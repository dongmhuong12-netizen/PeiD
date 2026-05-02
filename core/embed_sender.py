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

# Hàng đợi reaction toàn cục (thread-safe với lock)
_reaction_queue = deque()
_queue_lock = asyncio.Lock()
_worker_task = None


# =========================
# QUEUE SYSTEM (CHỐNG RATE LIMIT CẤP ĐỘ BOT LỚN) - GIỮ NGUYÊN 100%
# =========================

async def _reaction_worker():
    """worker duy nhất xử lý hàng đợi reaction toàn cục"""
    try:
        while True:
            if not _reaction_queue:
                await asyncio.sleep(0.5)
                continue

            try:
                message, emoji = _reaction_queue.popleft()
                # kiểm tra quyền hạn trước khi add để tránh lỗi rác log
                await message.add_reaction(emoji)
                
                # nghỉ 0.3s chuẩn discord api (an toàn tuyệt đối cho bot lớn)
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                print(f"[queue error] thiếu quyền add reaction tại channel {message.channel.id}", flush=True)
            except discord.HTTPException as e:
                if e.status == 429: # dính rate limit
                    retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                    print(f"[rate limit] nghỉ {retry_after}s theo yêu cầu discord...", flush=True)
                    await asyncio.sleep(retry_after)
            except Exception:
                pass
    except asyncio.CancelledError:
        # dừng worker êm ái khi module bị unload
        pass


async def _enqueue_reaction(message, emoji):
    """đẩy reaction vào hàng đợi an toàn"""
    async with _queue_lock:
        _reaction_queue.append((message, emoji))

    global _worker_task
    if _worker_task is None or _worker_task.done():
        # khởi tạo worker nếu chưa có hoặc đã chết
        _worker_task = asyncio.create_task(_reaction_worker())


# =========================
# EMBED BUILDER (NÂNG CẤP ĐỒNG BỘ UI PRO)
# =========================

def _build_embed(embed_copy: dict):
    """hàm xây dựng đối tượng embed nguyên tử - đã đồng bộ tông màu f8bbd0"""
    color = embed_copy.get("color")
    if isinstance(color, str):
        try:
            color = int(color.replace("#", "").replace("0x", ""), 16)
        except:
            color = 0xf8bbd0
    
    # mặc định về màu hồng f8bbd0 nếu không có màu cụ thể
    embed = discord.Embed(
        title=embed_copy.get("title"),
        description=embed_copy.get("description"),
        color=color if color not in [0x5865F2, None] else 0xf8bbd0
    )

    # --- mạch timestamp (chỉ kích hoạt khi nhập yes) ---
    if embed_copy.get("timestamp") == "yes":
        embed.timestamp = discord.utils.utcnow()

    # xử lý image/thumbnail (giữ nguyên logic gốc)
    for attr in ["image", "thumbnail"]:
        val = embed_copy.get(attr)
        if val:
            url = val.get("url") if isinstance(val, dict) else val
            if url and str(url).startswith("http"):
                getattr(embed, f"set_{attr}")(url=url)

    # xử lý footer (thêm icon url)
    footer = embed_copy.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        f_icon = footer.get("icon_url")
        embed.set_footer(
            text=footer["text"],
            icon_url=f_icon if f_icon and str(f_icon).startswith("http") else None
        )

    # xử lý author (thêm icon url & link url)
    author = embed_copy.get("author")
    if isinstance(author, dict) and author.get("name"):
        a_icon = author.get("icon_url")
        a_url = author.get("url")
        embed.set_author(
            name=author["name"],
            icon_url=a_icon if a_icon and str(a_icon).startswith("http") else None,
            url=a_url if a_url and str(a_url).startswith("http") else None
        )

    # xử lý fields (giữ nguyên logic gốc)
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
# SEND EMBED CORE (CẬP NHẬT PHASE 3)
# =========================

async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction, discord.Thread],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None,
    only_build: bool = False,
    view: discord.ui.View | None = None
):
    """
    xử lý gửi embed và đăng ký liên kết vào não bộ state.
    """
    if not isinstance(embed_data, dict) or not embed_data:
        return None

    try:
        # 1. apply biến động (user/server variables)
        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        # 2. build đối tượng embed
        embed = _build_embed(embed_copy)
        if only_build:
            return embed

        # [CẬP NHẬT PHASE 3] Tự động tạo View nếu trong data có nút bấm mà view truyền vào là None
        if view is None:
            buttons_data = embed_data.get("buttons", [])
            if buttons_data:
                view = discord.ui.View(timeout=None)
                for btn in buttons_data:
                    if btn.get("type") == "link":
                        view.add_item(discord.ui.Button(label=btn["label"], url=btn["url"]))

        # 3. gửi tin nhắn an toàn
        message = None
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                message = await destination.followup.send(embed=embed, view=view)
            else:
                await destination.response.send_message(embed=embed, view=view)
                message = await destination.original_response()
        else:
            # check quyền gửi embed trước khi gửi
            perms = destination.permissions_for(guild.me)
            if not perms.send_messages or not perms.embed_links:
                print(f"[send error] bot thiếu quyền gửi embed tại channel {destination.id}", flush=True)
                return False
            message = await destination.send(embed=embed, view=view)

        if not message:
            return False

        # 4. đăng ký trí nhớ (bắt buộc để reaction role hoạt động)
        if embed_name:
            await State.atomic_embed_register(guild.id, embed_name, message.id)

        # 5. xử lý reaction roles (nếu có cấu hình)
        reaction_db = get_raw(REACTION_FILE_KEY)
        storage_key = f"{guild.id}:{embed_name}"
        config = reaction_db.get(storage_key)

        if config:
            # chép cấu hình sang id tin nhắn để listener tra cứu thần tốc
            reaction_db[str(message.id)] = config
            mark_dirty(REACTION_FILE_KEY)

            # thả reaction vào hàng đợi
            for group in config.get("groups", []):
                for emoji in group.get("emojis", []):
                    await _enqueue_reaction(message, emoji)

        return True

    except Exception as e:
        print(f"[embed send error] {e}", flush=True)
        return False

# [VÁ LỖI] Giải phóng RAM và tác vụ ngầm khi reload
async def teardown(bot):
    """dọn dẹp worker khi module bị unload/reload để tránh rò rỉ tác vụ"""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    print("[unload] success: core.embed_sender", flush=True)


