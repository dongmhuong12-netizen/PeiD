import discord
from discord.ext import commands
from discord import app_commands
import json
import os

from boost_handler import send_boost

CONFIG_FILE = "boost_config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class BoostSystemV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()

    def get_guild_config(self, guild_id):
        return self.config.setdefault(str(guild_id), {})

    # =============================
    # SLASH COMMANDS V2
    # =============================

    @app_commands.command(name="setchannel", description="Set kênh boost")
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_conf = self.get_guild_config(interaction.guild.id)
        guild_conf["channel_id"] = channel.id
        save_config(self.config)
        await interaction.response.send_message("✅ Đã set kênh boost.")

    @app_commands.command(name="setrole", description="Set role boost")
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        guild_conf = self.get_guild_config(interaction.guild.id)
        guild_conf["role_id"] = role.id
        save_config(self.config)
        await interaction.response.send_message("✅ Đã set role boost.")

    @app_commands.command(name="setmessage", description="Set lời cảm ơn")
    async def setmessage(self, interaction: discord.Interaction, message: str):
        guild_conf = self.get_guild_config(interaction.guild.id)
        guild_conf["message"] = message
        save_config(self.config)
        await interaction.response.send_message("✅ Đã set lời cảm ơn.")

    @app_commands.command(name="setimage", description="Thêm gif boost")
    async def setimage(self, interaction: discord.Interaction, url: str):
        guild_conf = self.get_guild_config(interaction.guild.id)
        guild_conf.setdefault("gifs", []).append(url)
        save_config(self.config)
        await interaction.response.send_message("✅ Đã thêm gif.")

    @app_commands.command(name="testboost", description="Test hệ thống boost")
    async def testboost(self, interaction: discord.Interaction):
        await send_boost(interaction.guild, interaction.user)
        await interaction.response.send_message("✅ Đã test boost.")

    # =============================
    # AUTO DETECT BOOST
    # =============================

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Khi user bắt đầu boost
        if before.premium_since is None and after.premium_since is not None:
            await send_boost(after.guild, after)

        # Khi user bỏ boost
        if before.premium_since is not None and after.premium_since is None:
            guild_conf = self.get_guild_config(after.guild.id)
            role_id = guild_conf.get("role_id")

            if role_id:
                role = after.guild.get_role(role_id)
                if role and role in after.roles:
                    await after.remove_roles(role)


async def setup(bot):
    await bot.add_cog(BoostSystemV2(bot))
