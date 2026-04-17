import discord
from discord import app_commands
from discord.ext import commands

from core.voice_manager import VoiceManager


class VoiceSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager: VoiceManager = bot.voice_manager

    # =========================
    # JOIN
    # =========================
    @app_commands.command(name="vjoin", description="Bot join voice channel bạn đang ở")
    async def vjoin(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message(
                "Bạn chưa ở voice channel",
                ephemeral=True
            )

        channel = interaction.user.voice.channel
        result = await self.manager.join(interaction, channel)

        if result is True:
            await interaction.response.send_message("Đã vào voice")
        elif result == "COOLDOWN":
            await interaction.response.send_message(
                "Đang cooldown, thử lại sau",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Lỗi: {result}",
                ephemeral=True
            )

    # =========================
    # LEAVE
    # =========================
    @app_commands.command(name="vleave", description="Bot rời voice channel")
    async def vleave(self, interaction: discord.Interaction):
        result = await self.manager.leave(interaction.guild)

        if result is True:
            await interaction.response.send_message("Đã rời voice")
        else:
            await interaction.response.send_message(
                f"Lỗi: {result}",
                ephemeral=True
            )

    # =========================
    # STATUS
    # =========================
    @app_commands.command(name="vstatus", description="Xem trạng thái voice bot")
    async def vstatus(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.response.send_message("Bot không ở voice")

        await interaction.response.send_message(
            f"Voice channel: {vc.channel.name}\nStatus: Connected"
        )


# =========================
# SETUP (QUAN TRỌNG)
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceSystem(bot))
