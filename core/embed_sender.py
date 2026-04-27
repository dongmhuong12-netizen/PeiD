import discord
import copy
import os
import asyncio
from typing import Union
from collections import deque
from core.variable_engine import apply_variables
from core.state import State
from core.cache_manager import get_raw, mark_dirty

# Key chuẩn cho hệ thống phản xạ 100k+
REACTION_FILE_KEY = "reaction_roles"

# Hàng đợi reaction toàn cục (Thread-safe với Lock)
_reaction_queue = deque()
_queue_lock = asyncio.Lock()
_worker_task = None


# =========================
# QUEUE SYSTEM (CHỐNG RATE LIMIT CẤP ĐỘ BOT LỚN) - GIỮ NGUYÊN 100%
# =========================

async def _reaction_worker():
    """Worker duy nhất xử lý hàng đợi reaction toàn cục"""
    while True:
        if not _reaction_queue:
            await asyncio.sleep(0.5)
            continue

        try:
            message, emoji = _reaction_queue.popleft()
            # Kiểm tra quyền hạn trước khi add để tránh lỗi rác Log
            await message.add_reaction(emoji)
            
            # Nghỉ 0.3s chuẩn Discord API (An toàn tuyệt đối cho Bot lớn)
            await asyncio.sleep(0.3)
        except discord.Forbidden:
            print(f"[QUEUE ERROR] Thiếu quyền Add Reaction tại channel {message.channel.id}", flush=True)
        except discord.HTTPException as e:
            if e.status == 429: # Dính Rate Limit
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                print(f"[RATE LIMIT] Nghỉ {retry_after}s theo yêu cầu Discord...", flush=True)
                await asyncio.sleep(retry_after)
        except Exception:
            pass


async def _enqueue_reaction(message, emoji):
    """Đẩy reaction vào hàng đợi an toàn"""
    async with _queue_lock:
        _reaction_queue.append((message, emoji))

    global _worker_task
    if _worker_task is None or _worker_task.done():
        # Khởi tạo worker nếu chưa có hoặc đã chết
        _worker_task = asyncio.create_task(_reaction_worker())


# =========================
# EMBED BUILDER (NÂNG CẤP ĐỒNG BỘ UI PRO)
# =========================

def _build_embed(embed_copy: dict):
    """Hàm xây dựng đối tượng Embed nguyên tử - Đã thêm mạch Author/Footer Icon"""
    color = embed_copy.get("color")
    if isinstance(color, str):
        try:
            color = int(color.replace("#", "").replace("0x", ""), 16)
        except:
            color = 0x5865F2
    
    embed = discord.Embed(
        title=embed_copy.get("title"),
        description=embed_copy.get("description"),
        color=color or 0x5865F2
    )

    # Xử lý Image/Thumbnail (GIỮ NGUYÊN LOGIC GỐC)
    for attr in ["image", "thumbnail"]:
        val = embed_copy.get(attr)
        if val:
            url = val.get("url") if isinstance(val, dict) else val
            if url and str(url).startswith("http"):
                getattr(embed, f"set_{attr}")(url=url)

    # Xử lý Footer (MỞ RỘNG: Thêm Icon URL)
    footer = embed_copy.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        f_icon = footer.get("icon_url")
        embed.set_footer(
            text=footer["text"],
            icon_url=f_icon if f_icon and str(f_icon).startswith("http") else None
        )

    # Xử lý Author (MỞ RỘNG: Thêm Icon URL & Link URL)
    author = embed_copy.get("author")
    if isinstance(author, dict) and author.get("name"):
        a_icon = author.get("icon_url")
        a_url = author.get("url")
        embed.set_author(
            name=author["name"],
            icon_url=a_icon if a_icon and str(a_icon).startswith("http") else None,
            url=a_url if a_url and str(a_url).startswith("http") else None
        )

    # Xử lý Fields (GIỮ NGUYÊN LOGIC GỐC)
    fields = embed_copy.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if field.get("name") and field.get("value"):
                embed.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field.get("inline", False)
                )
    return embed


# =========================
# SEND EMBED CORE (GIỮ NGUYÊN 100% LOGIC CỦA NGUYỆT)
# =========================

async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction, discord.Thread],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None,
    only_build: bool = False
):
    """
    Xử lý gửi Embed và đăng ký liên kết vào não bộ State.
    """
    if not isinstance(embed_data, dict) or not embed_data:
        return None

    try:
        # 1. Apply biến động (User/Server variables)
        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        # 2. Build đối tượng Embed
        embed = _build_embed(embed_copy)
        if only_build:
            return embed

        # 3. Gửi tin nhắn an toàn
        message = None
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                message = await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
                message = await destination.original_response()
        else:
            # Check quyền gửi Embed trước khi gửi
            perms = destination.permissions_for(guild.me)
            if not perms.send_messages or not perms.embed_links:
                print(f"[SEND ERROR] Bot thiếu quyền gửi Embed tại channel {destination.id}", flush=True)
                return False
            message = await destination.send(embed=embed)

        if not message:
            return False

        # 4. ĐĂNG KÝ TRÍ NHỚ (Bắt buộc để Reaction Role hoạt động)
        if embed_name:
            await State.atomic_embed_register(guild.id, embed_name, message.id)

        # 5. XỬ LÝ REACTION ROLES (Nếu có cấu hình)
        reaction_db = get_raw(REACTION_FILE_KEY)
        storage_key = f"{guild.id}:{embed_name}"
        config = reaction_db.get(storage_key)

        if config:
            # Chép cấu hình sang ID tin nhắn để Listener tra cứu thần tốc
            reaction_db[str(message.id)] = config
            mark_dirty(REACTION_FILE_KEY)

            # Thả reaction vào hàng đợi
            for group in config.get("groups", []):
                for emoji in group.get("emojis", []):
                    await _enqueue_reaction(message, emoji)

        return True

    except Exception as e:
        print(f"[EMBED SEND ERROR] {e}", flush=True)
        return False
