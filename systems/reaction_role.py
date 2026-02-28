import discord
from discord.ext import commands
import json
import os

DATA_FILE = "data/reaction_roles.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def refresh(self):
        return load_data()

    # =========================
    # REACTION ADD
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        data = self.refresh()
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)

        guild_configs = [
            v for v in data.values()
            if v.get("guild_id") == guild_id
        ]

        if not guild_configs:
            return

        for config in guild_configs:
            for group in config.get("groups", []):

                if emoji_str not in group["emojis"]:
                    continue

                index = group["emojis"].index(emoji_str)
                role_data = group["roles"][index]

                role_ids = role_data if isinstance(role_data, list) else [role_data]

                roles_to_add = []
                for r_id in role_ids:
                    try:
                        role = guild.get_role(int(r_id))
                        if role:
                            roles_to_add.append(role)
                    except:
                        continue

                if not roles_to_add:
                    continue

                # =========================
                # MULTI MODE
                # =========================
                if group["mode"] == "multi":
                    try:
                        await member.add_roles(*roles_to_add)
                    except:
                        pass

                # =========================
                # SINGLE MODE (FIXED)
                # =========================
                elif group["mode"] == "single":

                    # 🔥 Remove toàn bộ role trong group trước
                    for r_data in group["roles"]:

                        ids = r_data if isinstance(r_data, list) else [r_data]

                        for rid in ids:
                            try:
                                r = guild.get_role(int(rid))
                                if r and r in member.roles:
                                    await member.remove_roles(r)
                            except:
                                pass

                    # 🔥 Remove các reaction khác của user trong cùng message
                    try:
                        channel = guild.get_channel(payload.channel_id)
                        message = await channel.fetch_message(payload.message_id)

                        for reaction in message.reactions:
                            if str(reaction.emoji) != emoji_str:
                                async for user in reaction.users():
                                    if user.id == member.id:
                                        await reaction.remove(member)
                    except:
                        pass

                    # 🔥 Add role mới
                    try:
                        await member.add_roles(*roles_to_add)
                    except:
                        pass

                return  # dừng sau khi xử lý


    # =========================
    # REACTION REMOVE
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        data = self.refresh()
        guild_id = payload.guild_id

        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)

        guild_configs = [
            v for v in data.values()
            if v.get("guild_id") == guild_id
        ]

        if not guild_configs:
            return

        for config in guild_configs:
            for group in config.get("groups", []):

                if emoji_str not in group["emojis"]:
                    continue

                index = group["emojis"].index(emoji_str)
                role_data = group["roles"][index]

                role_ids = role_data if isinstance(role_data, list) else [role_data]

                roles_to_remove = []

                for r_id in role_ids:
                    try:
                        role = guild.get_role(int(r_id))
                        if role:
                            roles_to_remove.append(role)
                    except:
                        continue

                if not roles_to_remove:
                    continue

                try:
                    await member.remove_roles(*roles_to_remove)
                except:
                    pass

                return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
