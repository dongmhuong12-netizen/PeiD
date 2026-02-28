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


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_data()

    # =========================
    # REACTION ADD
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        message_id = str(payload.message_id)

        if message_id not in self.data:
            return

        config = self.data[message_id]
        guild = self.bot.get_guild(config["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)

        # 🔥 DUYỆT TỪNG GROUP
        for group in config.get("groups", []):

            if emoji_str not in group["emojis"]:
                continue

            index = group["emojis"].index(emoji_str)
            role_id = group["roles"][index]
            role = guild.get_role(role_id)

            if not role:
                return

            # ===== MULTI MODE =====
            if group["mode"] == "multi":
                try:
                    await member.add_roles(role)
                except:
                    pass

            # ===== SINGLE MODE =====
            elif group["mode"] == "single":

                # remove tất cả role trong group trước
                for r_id in group["roles"]:
                    r = guild.get_role(r_id)
                    if r and r in member.roles:
                        try:
                            await member.remove_roles(r)
                        except:
                            pass

                # add role mới
                try:
                    await member.add_roles(role)
                except:
                    pass

            return  # xử lý xong thì thoát

    # =========================
    # REACTION REMOVE
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        message_id = str(payload.message_id)

        if message_id not in self.data:
            return

        config = self.data[message_id]
        guild = self.bot.get_guild(config["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)

        for group in config.get("groups", []):

            if emoji_str not in group["emojis"]:
                continue

            index = group["emojis"].index(emoji_str)
            role_id = group["roles"][index]
            role = guild.get_role(role_id)

            if not role:
                return

            # chỉ remove nếu là multi
            if group["mode"] == "multi":
                try:
                    await member.remove_roles(role)
                except:
                    pass

            # nếu single thì không làm gì khi remove reaction
            # vì role đã được xử lý ở add

            return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
