import discord
import copy
import os
import json
import asyncio
from typing import Union
from collections import defaultdict, deque
from core.variable_engine import apply_variables

from core.state import State

DATA_FILE = "data/reaction_roles.json"

file_lock = asyncio.Lock()

# =========================
# CACHE LAYER
# =========================

_reaction_cache = None
_cache_loaded = False
_cache_lock = asyncio.Lock()

_restore_lock_map = defaultdict(asyncio.Lock)

_reaction_queue = deque()
_queue_lock = asyncio.Lock()
_queue_worker_started = False


# =========================
# LOAD JSON
# =========================

def load_reaction_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
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


# =========================
# QUEUE SYSTEM
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

        await asyncio.sleep(0.18)


async def _enqueue_reaction(message, emoji):
    async with _queue_lock:
        _reaction_queue.append((message, emoji))

    global _queue_worker_started
    if not _queue_worker_started:
        _queue_worker_started = True
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
        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        embed = _build_embed(embed_copy)

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
        # REACTION RESTORE (FIXED ARCHITECTURE)
        # =========================

        await _load_cache()

        msg_id = str(message.id)
        lock = _restore_lock_map[msg_id]

        async with lock:

            # SOURCE OF TRUTH FIRST
            data = load_reaction_data()

            # STATE = CACHE ONLY (NO AUTHORITY)
            state_config = await State.get_reaction(message.id)

            config = data.get(msg_id)

            if not isinstance(config, dict):
                if isinstance(state_config, dict):
                    config = state_config

            # RESTORE
            if isinstance(config, dict) and "groups" in config:

                for group in config.get("groups", []):
                    for emoji in group.get("emojis", []):
                        await _enqueue_reaction(message, emoji)

            # INIT NEW
            else:
                new_config = {
                    "guild_id": guild.id,
                    "channel_id": message.channel.id,
                    "embed_name": embed_name,
                    "groups": []
                }

                data[msg_id] = new_config
                await save_reaction_data(data)

                await State.set_reaction(message.id, new_config)

            # SYNC STATE IF MISSING
            if isinstance(config, dict) and not state_config:
                await State.set_reaction(message.id, config)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
