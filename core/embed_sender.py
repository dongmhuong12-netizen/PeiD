# core/embed_sender.py
import discord
import copy
import os
import json
import asyncio
from typing import Union
from collections import defaultdict, deque
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"

file_lock = asyncio.Lock()

# =========================
# CACHE LAYER (GLOBAL SAFE)
# =========================

_reaction_cache = None
_cache_loaded = False
_cache_lock = asyncio.Lock()

# per-message restore lock (anti duplicate restore)
_restore_lock_map = defaultdict(asyncio.Lock)

# reaction queue (anti rate-limit burst)
_reaction_queue = deque()
_queue_lock = asyncio.Lock()
_queue_worker_started = False


# =========================
# CACHE LOAD
# =========================

def load_reaction_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


async def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)

    tmp = DATA_FILE + ".tmp"

    async with file_lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        os.replace(tmp, DATA_FILE)

        global _reaction_cache, _cache_loaded
        _reaction_cache = data
        _cache_loaded = True


async def _load_cache():
    global _reaction_cache, _cache_loaded

    async with _cache_lock:
        if not _cache_loaded:
            _reaction_cache = load_reaction_data()
            _cache_loaded = True


def _sync_cache():
    global _reaction_cache
    _reaction_cache = load_reaction_data()


# =========================
# REACTION QUEUE WORKER
# =========================

async def _reaction_worker():
    global _queue_worker_started

    while True:
        if not _reaction_queue:
            await asyncio.sleep(0.1)
            continue

        message, emoji = _reaction_queue.popleft()

        try:
            await message.add_reaction(emoji)
        except:
            pass

        await asyncio.sleep(0.18)  # anti rate limit stable


async def _enqueue_reaction(message, emoji):
    async with _queue_lock:
        _reaction_queue.append((message, emoji))

    global _queue_worker_started
    if not _queue_worker_started:
        _queue_worker_started = True
        asyncio.create_task(_reaction_worker())


# =========================
# EMBED BUILDER SAFE
# =========================

def _build_embed(embed_copy: dict):
    color = embed_copy.get("color")

    if isinstance(color, str):
        try:
            color = int(color.replace("#", "").replace("0x", ""), 16)
        except:
            color = 0x2F3136

    return discord.Embed(
        title=embed_copy.get("title"),
        description=embed_copy.get("description"),
        color=color or 0x2F3136
    )


# =========================
# SEND EMBED CORE
# =========================

async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None
):

    if not isinstance(embed_data, dict) or not embed_data:
        return False

    try:
        # resolve member
        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        # variable engine
        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        embed = _build_embed(embed_copy)

        # optional parts
        image = embed_copy.get("image")
        if image:
            embed.set_image(url=image.get("url") if isinstance(image, dict) else image)

        thumbnail = embed_copy.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.get("url") if isinstance(thumbnail, dict) else thumbnail)

        footer = embed_copy.get("footer")
        if isinstance(footer, dict):
            embed.set_footer(text=footer.get("text"))

        author = embed_copy.get("author")
        if isinstance(author, dict):
            embed.set_author(name=author.get("name"))

        fields = embed_copy.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if field.get("name") and field.get("value"):
                    embed.add_field(
                        name=field["name"],
                        value=field["value"],
                        inline=field.get("inline", False)
                    )

    except Exception as e:
        print("Embed build error:", e)
        return False

    try:
        # =========================
        # SEND MESSAGE
        # =========================

        if isinstance(destination, discord.Interaction):

            if destination.response.is_done():
                message = await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
                message = await destination.original_response()

        else:
            bot_member = guild.me
            if not bot_member:
                return False

            perms = destination.permissions_for(bot_member)
            if not (perms.send_messages and perms.embed_links):
                return False

            message = await destination.send(embed=embed)

        # =========================
        # REACTION RESTORE + INIT (FIXED, KHÔNG MẤT LOGIC)
        # =========================

        await _load_cache()

        data = _reaction_cache or load_reaction_data()
        msg_id = str(message.id)

        lock = _restore_lock_map[msg_id]

        async with lock:

            config = data.get(msg_id)

            # CASE 1: đã có config → restore reaction
            if isinstance(config, dict) and "groups" in config:

                for group in config.get("groups", []):
                    for emoji in group.get("emojis", []):
                        await _enqueue_reaction(message, emoji)

            # CASE 2: chưa có → tạo mới (giữ logic cũ)
            else:
                data[msg_id] = {
                    "guild_id": guild.id,
                    "channel_id": message.channel.id,
                    "embed_name": embed_name,
                    "groups": []
                }

                await save_reaction_data(data)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
