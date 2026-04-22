import discord
from discord.ext import commands
import asyncio
import time
from collections import deque

from core.cache_manager import load, mark_dirty
from core.state import State

FILE_KEY = "reaction_roles"

# =========================
# EVENT DEDUP (UNCHANGED LOGIC)
# =========================

EVENT_TTL = 60
_event_log = deque()
_event_set = set()
_event_lock = asyncio.Lock()


def _cleanup_events():
    now = time.time()

    while _event_log:
        if now - _event_log[0][0] <= EVENT_TTL:
            break
        _, key = _event_log.popleft()
        _event_set.discard(key)


async def _is_duplicate(key: str):
    async with _event_lock:
        _cleanup_events()
        return key in _event_set


async def _mark_event(key: str):
    async with _event_lock:
        _cleanup_events()
        _event_set.add(key)
        _event_log.append((time.time(), key))


# =========================
# NORMALIZER
# =========================

def _normalize_emoji(e) -> str:
    if isinstance(e, str):
        return e.strip()
    return str(e).strip()


def _emoji_key(payload_emoji) -> str:
    return _normalize_emoji(payload_emoji)


def _normalize_roles(roles):
    result = []

    if isinstance(roles, list):
        for r in roles:
            result.append(str(r))
    else:
        result = [str(roles)]

    return result


# =========================
# CORE COG
# =========================

class ReactionRole(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.data = load(FILE_KEY) or {}

        self.emoji_map = {}
        self.group_roles = {}

        self.message_cache = {}
        self._cache_limit = 200

    # =========================
    # REFRESH
    # =========================

    def _refresh(self):
        self.data = load(FILE_KEY) or {}
        self.build_cache()

    # =========================
    # READY
    # =========================

    @commands.Cog.listener()
    async def on_ready(self):
        self._refresh()
        print("ReactionRole SAFE PATCH LOADED")

    # =========================
    # CACHE BUILD (FIXED)
    # =========================

    def build_cache(self):
        self.emoji_map.clear()
        self.group_roles.clear()

        for msg_id, config in self.data.items():

            msg_id = str(msg_id)

            self.emoji_map[msg_id] = {}
            self.group_roles[msg_id] = set()

            for group in config.get("groups", []):

                emojis = [_normalize_emoji(e) for e in group.get("emojis", [])]

                role_ids = _normalize_roles(group.get("roles", []))

                group_data = {
                    "roles": role_ids,
                    "mode": group.get("mode", "multi"),
                    "group_emojis": emojis
                }

                for emoji in emojis:
                    self.emoji_map[msg_id][emoji] = group_data

                for r in role_ids:
                    self.group_roles[msg_id].add(str(r))

    # =========================
    # ATTACH
    # =========================

    async def attach_reactions(self, message: discord.Message):
        config = self.data.get(str(message.id))
        if not config:
            return

        for group in config.get("groups", []):
            for emoji in group.get("emojis", []):
                try:
                    await message.add_reaction(_normalize_emoji(emoji))
                    await asyncio.sleep(0.1)
                except:
                    pass

        self.message_cache[str(message.id)] = message

    # =========================
    # ADD REACTION
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        key = f"{payload.user_id}:{payload.message_id}:{_emoji_key(payload.emoji)}"

        if await _is_duplicate(key):
            return
        await _mark_event(key)

        msg_id = str(payload.message_id)

        if msg_id not in self.emoji_map:
            self._refresh()
            if msg_id not in self.emoji_map:
                return

        emoji = _emoji_key(payload.emoji)

        if emoji not in self.emoji_map[msg_id]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        bot_member = guild.me
        if not bot_member:
            return

        data = self.emoji_map[msg_id][emoji]

        roles_to_add = []

        for rid in data["roles"]:
            role = guild.get_role(int(rid))
            if role and role < bot_member.top_role:
                roles_to_add.append(role)

        if not roles_to_add:
            return

        if data["mode"] == "single":

            roles_to_remove = []

            for rid in self.group_roles.get(msg_id, []):
                role = guild.get_role(int(rid))

                if role and role in member.roles and role < bot_member.top_role:
                    if role not in roles_to_add:
                        roles_to_remove.append(role)

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            message = self.message_cache.get(msg_id)

            if not message:
                channel = guild.get_channel(payload.channel_id)
                if not channel:
                    return

                try:
                    message = await channel.fetch_message(payload.message_id)

                    if len(self.message_cache) >= self._cache_limit:
                        self.message_cache.clear()

                    self.message_cache[msg_id] = message

                except:
                    self.data.pop(msg_id, None)
                    mark_dirty(FILE_KEY)
                    self._refresh()
                    return

            for old_emoji in data["group_emojis"]:
                if old_emoji == emoji:
                    continue

                for r in message.reactions:
                    if _normalize_emoji(r.emoji) == old_emoji:
                        try:
                            await r.remove(member)
                        except:
                            pass

        await member.add_roles(*roles_to_add)

    # =========================
    # REMOVE REACTION
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        if not payload.guild_id:
            return

        msg_id = str(payload.message_id)

        if msg_id not in self.emoji_map:
            self._refresh()
            if msg_id not in self.emoji_map:
                return

        emoji = _emoji_key(payload.emoji)

        if emoji not in self.emoji_map[msg_id]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        bot_member = guild.me
        if not bot_member:
            return

        data = self.emoji_map[msg_id][emoji]

        roles_to_remove = []

        for rid in data["roles"]:
            role = guild.get_role(int(rid))
            if role and role < bot_member.top_role:
                roles_to_remove.append(role)

        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
