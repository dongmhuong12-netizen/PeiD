import discord
from discord import app_commands
from discord.ext import commands

from core.voice_manager import VoiceManager


class VoiceSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = bot.voice_manager

    @app_commands.command(name="vjoin")
    async def vjoin(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("Bạn chưa ở voice", ephemeral=True)

        result = await self.manager.join(interaction, interaction.user.voice.channel)

        if result is True:
            await interaction.response.send_message("Đã vào voice")
        elif result == "COOLDOWN":
            await interaction.response.send_message("Cooldown", ephemeral=True)
        else:
            await interaction.response.send_message(f"Lỗi: {result}", ephemeral=True)

    @app_commands.command(name="vleave")
    async def vleave(self, interaction: discord.Interaction):
        result = await self.manager.leave(interaction.guild)

        await interaction.response.send_message("Đã rời voice" if result is True else str(result))

    @app_commands.command(name="vstatus")
    async def vstatus(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("Bot không ở voice")
        await interaction.response.send_message(vc.channel.name)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceSystem(bot))
