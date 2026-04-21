# systems/reaction_role.py
import discord
from discord.ext import commands
import json
import os
import asyncio
import tempfile

DATA_FILE = "data/reaction_roles.json"

file_lock = asyncio.Lock()

# =========================
# WAKE CACHE LAYER (NEW)
# =========================

_cache = None
_cache_loaded = False


def _load_cache():
    global _cache, _cache_loaded

    if not _cache_loaded:
        _cache = load_data()
        _cache_loaded = True


def _sync_cache():
    global _cache
    _cache = load_data()


# =========================
# STORAGE
# =========================

def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


async def save_data(data):
    os.makedirs("data", exist_ok=True)

    async with file_lock:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir="data",
            encoding="utf-8"
        ) as tmp:
            json.dump(data, tmp, indent=4)
            temp_name = tmp.name

        os.replace(temp_name, DATA_FILE)

        # 🔥 sync cache sau save
        global _cache, _cache_loaded
        _cache = data
        _cache_loaded = True


# =========================
# CORE COG
# =========================

class ReactionRole(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()

        self.emoji_map = {}
        self.group_roles = {}
        self.message_cache = {}

    # =========================
    # READY
    # =========================

    @commands.Cog.listener()
    async def on_ready(self):
        self.data = load_data()
        self.build_cache()
        print("ReactionRole optimized system loaded")

    # =========================
    # CACHE BUILD
    # =========================

    def build_cache(self):
        self.emoji_map.clear()
        self.group_roles.clear()

        for msg_id, config in self.data.items():

            if not msg_id.isdigit():
                continue

            self.emoji_map[msg_id] = {}
            self.group_roles[msg_id] = []

            for group in config.get("groups", []):

                for emoji, role_data in zip(group["emojis"], group["roles"]):

                    role_ids = role_data if isinstance(role_data, list) else [role_data]

                    self.emoji_map[msg_id][emoji] = {
                        "roles": role_ids,
                        "mode": group.get("mode", "multi"),
                        "group_emojis": group["emojis"]
                    }

                    self.group_roles[msg_id].extend(role_ids)

    # =========================
    # ATTACH REACTIONS
    # =========================

    async def attach_reactions(self, message: discord.Message):
        config = self.data.get(str(message.id))

        if not config:
            return

        for group in config.get("groups", []):
            for emoji in group.get("emojis", []):
                try:
                    await message.add_reaction(emoji)
                    await asyncio.sleep(0.2)
                except:
                    pass

        self.message_cache[message.id] = message

    # =========================
    # ADD REACTION
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        msg_id = str(payload.message_id)

        if msg_id not in self.emoji_map:
            self.data = load_data()
            self.build_cache()

            if msg_id not in self.emoji_map:
                return

        emoji = str(payload.emoji)

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

        # =========================
        # SINGLE MODE LOGIC (UNCHANGED)
        # =========================

        if data["mode"] == "single":

            roles_to_remove = []

            for rid in self.group_roles[msg_id]:
                role = guild.get_role(int(rid))

                if role and role in member.roles and role < bot_member.top_role:
                    if role not in roles_to_add:
                        roles_to_remove.append(role)

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            message = self.message_cache.get(payload.message_id)

            if not message:
                channel = guild.get_channel(payload.channel_id)
                if not channel:
                    return

                try:
                    message = await channel.fetch_message(payload.message_id)
                    self.message_cache[payload.message_id] = message
                except:

                    if msg_id in self.data:
                        del self.data[msg_id]
                        await save_data(self.data)
                        self.build_cache()

                    return

            for old_emoji in data["group_emojis"]:

                if str(old_emoji) == emoji:
                    continue

                for r in message.reactions:
                    if str(r.emoji) == str(old_emoji):
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
            self.data = load_data()
            self.build_cache()

            if msg_id not in self.emoji_map:
                return

        emoji = str(payload.emoji)

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
