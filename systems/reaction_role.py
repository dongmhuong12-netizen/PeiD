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

        guild_id = payload.guild_id
        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        emoji_str = str(payload.emoji)
        data = self.refresh()

        for config in data.values():

            if config.get("guild_id") != guild_id:
                continue

            for group in config.get("groups", []):

                if emoji_str not in group.get("emojis", []):
                    continue

                index = group["emojis"].index(emoji_str)
                role_data = group["roles"][index]
                role_ids = role_data if isinstance(role_data, list) else [role_data]

                roles = []
                for rid in role_ids:
                    role = guild.get_role(int(rid))
                    if role:
                        roles.append(role)

                if not roles:
                    return

                # ===== SINGLE MODE =====
                if group.get("mode") == "single":

                    # remove role khác trong cùng group
                    for r_data in group["roles"]:
                        ids = r_data if isinstance(r_data, list) else [r_data]

                        for rid in ids:
                            r = guild.get_role(int(rid))
                            if r and r in member.roles and r not in roles:
                                await member.remove_roles(r)

                # ===== MULTI MODE =====
                # không remove gì

                # add role nếu chưa có
                for role in roles:
                    if role not in member.roles:
                        await member.add_roles(role)

                return

    # =========================
    # REACTION REMOVE
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        guild_id = payload.guild_id
        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        emoji_str = str(payload.emoji)
        data = self.refresh()

        for config in data.values():

            if config.get("guild_id") != guild_id:
                continue

            for group in config.get("groups", []):

                if emoji_str not in group.get("emojis", []):
                    continue

                index = group["emojis"].index(emoji_str)
                role_data = group["roles"][index]
                role_ids = role_data if isinstance(role_data, list) else [role_data]

                for rid in role_ids:
                    role = guild.get_role(int(rid))
                    if role and role in member.roles:
                        await member.remove_roles(role)

                return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
