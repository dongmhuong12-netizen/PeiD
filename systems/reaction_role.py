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
    # RELOAD DATA
    # =========================
    def refresh(self):
        self.data = load_data()

    # =========================
    # REACTION ADD
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.user_id == self.bot.user.id:
            return

        self.refresh()

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
            role_data = group["roles"][index]

            if not isinstance(role_data, list):
                role_ids = [role_data]
            else:
                role_ids = role_data

            roles_to_add = []

            for r_id in role_ids:
                try:
                    role = guild.get_role(int(r_id))
                    if role:
                        roles_to_add.append(role)
                except:
                    continue

            if not roles_to_add:
                break

            # ===== MULTI MODE =====
            if group["mode"] == "multi":
                try:
                    await member.add_roles(*roles_to_add)
                except:
                    pass

            # ===== SINGLE MODE =====
            elif group["mode"] == "single":

                # remove tất cả role trong group trước
                for r_data in group["roles"]:

                    if isinstance(r_data, list):
                        for sub_id in r_data:
                            try:
                                r = guild.get_role(int(sub_id))
                                if r and r in member.roles:
                                    await member.remove_roles(r)
                            except:
                                pass
                    else:
                        try:
                            r = guild.get_role(int(r_data))
                            if r and r in member.roles:
                                await member.remove_roles(r)
                        except:
                            pass

                try:
                    await member.add_roles(*roles_to_add)
                except:
                    pass

            break  # 🔥 chỉ break loop, không return

    # =========================
    # REACTION REMOVE
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        self.refresh()

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
            role_data = group["roles"][index]

            if not isinstance(role_data, list):
                role_ids = [role_data]
            else:
                role_ids = role_data

            roles_to_remove = []

            for r_id in role_ids:
                try:
                    role = guild.get_role(int(r_id))
                    if role:
                        roles_to_remove.append(role)
                except:
                    continue

            if not roles_to_remove:
                break

            try:
                await member.remove_roles(*roles_to_remove)
            except:
                pass

            break  # 🔥 break thay vì return


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
