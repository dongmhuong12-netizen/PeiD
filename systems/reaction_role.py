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
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except:
                return

        if member.bot:
            return

        data = self.refresh()

        # 🔥 LẤY CONFIG THEO MESSAGE.ID
        config = data.get(str(payload.message_id))
        if not config:
            return

        if int(config.get("guild_id")) != guild_id:
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

            # SINGLE MODE
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

                # Remove emoji cũ
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

        guild_id = payload.guild_id
        if not guild_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except:
                return

        if member.bot:
            return

        data = self.refresh()

        config = data.get(str(payload.message_id))
        if not config:
            return

        if int(config.get("guild_id")) != guild_id:
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
