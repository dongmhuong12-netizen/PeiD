import discord
from discord import app_commands
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
    # TEST COMMAND
    # =========================
    @app_commands.command(name="rr_test", description="Test reaction role system")
    async def rr_test(self, interaction: discord.Interaction):

        if not interaction.guild:
            return

        # ⚠ đổi 3 role này thành role ID thật trong server của cậu
        role_ids = [
            1475556354096894052,
            1475556479980273664,
            1475556621081116695
        ]

        emojis = ["🐋", "🐬", "🐳"]

        embed = discord.Embed(
            title="Reaction Role Test",
            description="Bấm emoji để nhận role.\nGỡ emoji để bỏ role.",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        # add reaction theo thứ tự
        for emoji in emojis:
            await message.add_reaction(emoji)

        # lưu config theo message_id
        self.data[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "roles": role_ids,
            "emojis": emojis
        }

        save_data(self.data)

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

        if str(payload.emoji) not in config["emojis"]:
            return

        guild = self.bot.get_guild(config["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        index = config["emojis"].index(str(payload.emoji))
        role_id = config["roles"][index]

        role = guild.get_role(role_id)
        if not role:
            return

        try:
            await member.add_roles(role)
        except:
            pass

    # =========================
    # REACTION REMOVE
    # =========================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):

        message_id = str(payload.message_id)

        if message_id not in self.data:
            return

        config = self.data[message_id]

        if str(payload.emoji) not in config["emojis"]:
            return

        guild = self.bot.get_guild(config["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        index = config["emojis"].index(str(payload.emoji))
        role_id = config["roles"][index]

        role = guild.get_role(role_id)
        if not role:
            return

        try:
            await member.remove_roles(role)
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
