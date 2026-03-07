import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/reaction_roles.json"


def load_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class ReactionRole(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()

        # cache
        self.emoji_map = {}
        self.group_roles = {}
        self.message_cache = {}


    @commands.Cog.listener()
    async def on_ready(self):
        self.data = load_data()
        self.build_cache()
        print("ReactionRole optimized system loaded")


    # =========================
    # BUILD CACHE
    # =========================

    def build_cache(self):

        self.emoji_map.clear()
        self.group_roles.clear()

        for msg_id, config in self.data.items():

            self.emoji_map[msg_id] = {}
            self.group_roles[msg_id] = []

            for group in config.get("groups", []):

                roles_in_group = []

                for emoji, role_data in zip(group["emojis"], group["roles"]):

                    role_ids = role_data if isinstance(role_data, list) else [role_data]

                    self.emoji_map[msg_id][emoji] = {
                        "roles": role_ids,
                        "mode": group.get("mode", "multi"),
                        "group_emojis": group["emojis"]
                    }

                    roles_in_group.extend(role_ids)

                self.group_roles[msg_id].extend(roles_in_group)


    # =========================
    # ADD REACTIONS
    # =========================

    async def attach_reactions(self, message: discord.Message):

        config = self.data.get(str(message.id))

        if not config:
            return

        for group in config.get("groups", []):
            for emoji in group.get("emojis", []):
                try:
                    await message.add_reaction(emoji)
                except:
                    pass

        self.message_cache[message.id] = message


    # =========================
    # REACTION ADD
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
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

        data = self.emoji_map[msg_id][emoji]

        roles_to_add = []

        for rid in data["roles"]:
            role = guild.get_role(int(rid))
            if role:
                roles_to_add.append(role)

        if not roles_to_add:
            return


        # =================
        # SINGLE MODE
        # =================

        if data["mode"] == "single":

            roles_to_remove = []

            for rid in self.group_roles[msg_id]:
                role = guild.get_role(int(rid))
                if role and role not in roles_to_add and role in member.roles:
                    roles_to_remove.append(role)

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)


            message = self.message_cache.get(payload.message_id)

            if not message:
                channel = guild.get_channel(payload.channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(payload.message_id)
                        self.message_cache[payload.message_id] = message
                    except:
                        message = None

            if message:

                for old_emoji in data["group_emojis"]:

                    if old_emoji == emoji:
                        continue

                    reaction = discord.utils.get(message.reactions, emoji=old_emoji)

                    if reaction:
                        try:
                            await reaction.remove(member)
                        except:
                            pass


        await member.add_roles(*roles_to_add)


    # =========================
    # REACTION REMOVE
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        msg_id = str(payload.message_id)

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

        data = self.emoji_map[msg_id][emoji]

        roles_to_remove = []

        for rid in data["roles"]:
            role = guild.get_role(int(rid))
            if role:
                roles_to_remove.append(role)

        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
