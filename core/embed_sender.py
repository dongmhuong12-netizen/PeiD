import discord
import copy
import os
import asyncio
from typing import Union
from collections import deque
from core.variable_engine import apply_variables
from core.state import State
from core.cache_manager import get_raw, mark_dirty

# Key dùng chung trong toàn hệ thống chuẩn 100k+ servers
REACTION_FILE_KEY = "reaction_roles"

# Hàng đợi reaction toàn cục
_reaction_queue = deque()
_queue_lock = asyncio.Lock()
_queue_worker_started = False


# =========================
# QUEUE SYSTEM (Quy tắc 2: Tối ưu chống Rate Limit)
# =========================

async def _reaction_worker():
    global _queue_worker_started
    while True:
        if not _reaction_queue:
            await asyncio.sleep(0.5)
            continue

        try:
            message, emoji = _reaction_queue.popleft()
            await message.add_reaction(emoji)
            # Nghỉ 0.25s chuẩn Discord API cho Bot lớn
            await asyncio.sleep(0.25)
        except discord.HTTPException:
            # Nếu dính Rate Limit nặng, nghỉ lâu hơn
            await asyncio.sleep(2)
        except Exception:
            pass


async def _enqueue_reaction(message, emoji):
    async with _queue_lock:
        _reaction_queue.append((message, emoji))

    global _queue_worker_started
    if not _queue_worker_started:
        _queue_worker_started = True
        # Khởi tạo worker trong vòng lặp sự kiện chính
        asyncio.create_task(_reaction_worker())


# =========================
# EMBED BUILDER
# =========================

def _build_embed(embed_copy: dict):
    color = embed_copy.get("color")
    if isinstance(color, str):
        try:
            color = int(color.replace("#", "").replace("0x", ""), 16)
        except:
            color = 0x5865F2 # Màu mặc định
    
    # Tạo đối tượng Embed cơ bản
    embed = discord.Embed(
        title=embed_copy.get("title"),
        description=embed_copy.get("description"),
        color=color or 0x5865F2
    )

    # Xử lý Image/Thumbnail/Footer/Author/Fields (Gom từ send_embed vào đây)
    for attr in ["image", "thumbnail"]:
        val = embed_copy.get(attr)
        if val:
            url = val.get("url") if isinstance(val, dict) else val
            getattr(embed, f"set_{attr}")(url=url)

    footer = embed_copy.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        embed.set_footer(text=footer["text"])

    author = embed_copy.get("author")
    if isinstance(author, dict) and author.get("name"):
        embed.set_author(name=author["name"])

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
# SEND EMBED CORE (Bản FULL Fix 10/10)
# =========================

async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction, None],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None,
    only_build: bool = False # Thêm flag để hỗ trợ gộp tin nhắn
):
    """
    Xử lý gửi Embed hoặc chỉ xây dựng (build) đối tượng Embed.
    """
    if not isinstance(embed_data, dict) or not embed_data:
        return None

    try:
        # 1. Chuẩn bị dữ liệu và Apply biến
        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        # Build đối tượng Embed
        embed = _build_embed(embed_copy)

        # Nếu chỉ yêu cầu build (để gộp tin nhắn), trả về đối tượng ngay
        if only_build:
            return embed

        # 2. Gửi tin nhắn (Nếu có destination)
        message = None
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                message = await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
                message = await destination.original_response()
        elif destination:
            bot_member = guild.me
            perms = destination.permissions_for(bot_member)
            if not (perms.send_messages and perms.embed_links):
                return False
            message = await destination.send(embed=embed)

        if not message:
            return False

        # 3. Đăng ký vào State bền vững (Chống mất trí nhớ)
        if embed_name:
            await State.atomic_embed_register(guild.id, embed_name, message.id)

        # 4. ĐỒNG BỘ REACTION ROLES
        reaction_db = get_raw(REACTION_FILE_KEY)
        storage_key = f"{guild.id}:{embed_name}"
        config = reaction_db.get(storage_key)

        if config and isinstance(config, dict):
            # Thả reaction qua hàng đợi Queue (Chống Rate Limit)
            groups = config.get("groups", [])
            for group in groups:
                for emoji in group.get("emojis", []):
                    await _enqueue_reaction(message, emoji)
            
            # Đăng ký ID tin nhắn vào State để Listener nhận diện được ngay
            await State.set_reaction(message.id, config)
            
            # Đồng bộ ngược vào DB để bền vững
            reaction_db[str(message.id)] = config
            mark_dirty(REACTION_FILE_KEY)

        return True

    except Exception as e:
        print(f"[Embed Send Error] {e}")
        return False
