import discord
from discord.ext import commands
import json
import os
import asyncio

DATA_FILE = "data/reaction_roles.json"


# =========================
# LOAD DATA
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# =========================
# SAVE DATA (THÊM)
# =========================

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class ReactionRole(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()
        self.lock = asyncio.Lock()


    # =========================
    # BOT READY
    # =========================

    @commands.Cog.listener()
    async def on_ready(self):

        await self.reload_data()

        print("ReactionRole data loaded")


    # =========================
    # RELOAD DATA
    # =========================

    async def reload_data(self):
        async with self.lock:
            self.data = load_data()


    # =========================
    # SAVE WRAPPER (THÊM)
    # =========================

    async def save(self):
        async with self.lock:
            save_data(self.data)


    # =========================
    # REACTION ADD
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        config = self.data.get(str(payload.message_id))

        if not config:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        if int(config.get("guild_id")) != guild.id:
            return

        member = guild.get_member(payload.user_id)

        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except:
                return

        if member.bot:
            return

        emoji_str = str(payload.emoji)

        for group in config.get("groups", []):

            if emoji_str not in group.get("emojis", []):
                continue

            index = group["emojis"].index(emoji_str)

            role_data = group["roles"][index]

            role_ids = role_data if isinstance(role_data, list) else [role_data]

            roles_to_add = []

            for rid in role_ids:

                role = guild.get_role(int(rid))

                if role:
                    roles_to_add.append(role)

            if not roles_to_add:
                return


            # =========================
            # SINGLE MODE
            # =========================

            if str(group.get("mode", "")).lower() == "single":

                group_roles = []

                for r_data in group["roles"]:

                    ids = r_data if isinstance(r_data, list) else [r_data]

                    for rid in ids:

                        role = guild.get_role(int(rid))

                        if role:
                            group_roles.append(role)

                roles_to_remove = [
                    r for r in group_roles
                    if r not in roles_to_add and r in member.roles
                ]

                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)


                # REMOVE OLD EMOJI
                channel = guild.get_channel(payload.channel_id)

                if channel:

                    try:
                        message = await channel.fetch_message(payload.message_id)

                        for reaction in message.reactions:

                            if str(reaction.emoji) != emoji_str:

                                async for user in reaction.users():

                                    if user.id == member.id:
                                        await reaction.remove(member)

                    except:
                        pass


            await member.add_roles(*roles_to_add)

            return


    # =========================
    # REACTION REMOVE
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        if not payload.guild_id:
            return

        config = self.data.get(str(payload.message_id))

        if not config:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        if int(config.get("guild_id")) != guild.id:
            return

        member = payload.member or guild.get_member(payload.user_id)

        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except:
                return

        if member.bot:
            return

        emoji_str = str(payload.emoji)

        for group in config.get("groups", []):

            if emoji_str not in group.get("emojis", []):
                continue

            index = group["emojis"].index(emoji_str)

            role_data = group["roles"][index]

            role_ids = role_data if isinstance(role_data, list) else [role_data]

            roles_to_remove = []

            for rid in role_ids:

                role = guild.get_role(int(rid))

                if role:
                    roles_to_remove.append(role)

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
