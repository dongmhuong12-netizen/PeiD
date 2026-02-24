import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random

CONFIG_FILE = "boost_config.json"

DEFAULT_COLOR = 0xF48FB1
DEFAULT_TITLE = "Woaaaa!! ✧˚₊‧"
DEFAULT_MESSAGE = "Cảm ơn {user} đã boost server ✨"
DEFAULT_GIFS = [
    "https://media.tenor.com/3vR6kG9yFZkAAAAC/anime-thank-you.gif"
]


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
        return self.config.get(str(guild_id), {})

    async def send_boost_embed(self, guild, user):
        guild_conf = self.get_guild_config(guild.id)

        channel_id = guild_conf.get("channel_id")
        role_id = guild_conf.get("role_id")
        color = guild_conf.get("color", DEFAULT_COLOR)
        title = guild_conf.get("title", DEFAULT_TITLE)
        message = guild_conf.get("message", DEFAULT_MESSAGE)
        gifs = guild_conf.get("gifs", DEFAULT_GIFS)

        channel = guild.get_channel(channel_id) if channel_id else None
        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=message.format(user=user.mention),
            color=discord.Color(color)
        )

        embed.set_image(url=random.choice(gifs))
        await channel.send(embed=embed)

        if role_id:
            role = guild.get_role(role_id)
            if role and role not in user.roles:
                await user.add_roles(role)

    # ===== COMMANDS =====

    @app_commands.command(name="setchannel", description="Set kênh boost")
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild.id)
        self.config.setdefault(guild_id, {})["channel_id"] = channel.id
        save_config(self.config)
        await interaction.response.send_message("Đã set kênh boost.")

    @app_commands.command(name="setrole", description="Set role boost")
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = str(interaction.guild.id)
        self.config.setdefault(guild_id, {})["role_id"] = role.id
        save_config(self.config)
        await interaction.response.send_message("Đã set role boost.")

    @app_commands.command(name="setmessage", description="Set lời cảm ơn")
    async def setmessage(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)
        self.config.setdefault(guild_id, {})["message"] = message
        save_config(self.config)
        await interaction.response.send_message("Đã set lời cảm ơn.")

    @app_commands.command(name="setimage", description="Thêm gif boost")
    async def setimage(self, interaction: discord.Interaction, url: str):
        guild_id = str(interaction.guild.id)
        guild_conf = self.config.setdefault(guild_id, {})
        guild_conf.setdefault("gifs", []).append(url)
        save_config(self.config)
        await interaction.response.send_message("Đã thêm gif.")

    @app_commands.command(name="testboost", description="Test hệ thống boost v2")
    async def testboost(self, interaction: discord.Interaction):
        await self.send_boost_embed(interaction.guild, interaction.user)
        await interaction.response.send_message("Đã test boost.")

    # ===== AUTO BOOST DETECT =====

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.premium_since is None and after.premium_since is not None:
            await self.send_boost_embed(after.guild, after)

        if before.premium_since is not None and after.premium_since is None:
            guild_conf = self.get_guild_config(after.guild.id)
            role_id = guild_conf.get("role_id")
            if role_id:
                role = after.guild.get_role(role_id)
                if role and role in after.roles:
                    await after.remove_roles(role)


async def setup(bot):
    await bot.add_cog(BoostSystemV2(bot))
