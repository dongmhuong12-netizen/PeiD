import discord
from discord import app_commands
from discord.ext import commands

from core.voice_manager import VoiceManager


class VoiceSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = bot.voice_manager

    # =========================
    # JOIN
    # =========================
    @app_commands.command(name="vjoin")
    async def vjoin(self, interaction: discord.Interaction):
        try:
            if not interaction.user.voice or not interaction.user.voice.channel:
                return await interaction.response.send_message(
                    "Bạn chưa ở voice channel.",
                    ephemeral=True
                )

            result = await self.manager.join(
                interaction,
                interaction.user.voice.channel
            )

            if result is True:
                await interaction.response.send_message("Đã vào voice.")
                return

            if result == "COOLDOWN":
                await interaction.response.send_message(
                    "Bạn đang thao tác quá nhanh, vui lòng chờ.",
                    ephemeral=True
                )
                return

            # không leak raw error nữa
            await interaction.response.send_message(
                "Không thể vào voice. Vui lòng thử lại.",
                ephemeral=True
            )

        except Exception:
            await interaction.response.send_message(
                "Có lỗi xảy ra khi xử lý lệnh voice.",
                ephemeral=True
            )

    # =========================
    # LEAVE
    # =========================
    @app_commands.command(name="vleave")
    async def vleave(self, interaction: discord.Interaction):
        try:
            result = await self.manager.leave(interaction.guild)

            if result is True:
                await interaction.response.send_message("Đã rời voice.")
            else:
                await interaction.response.send_message(
                    "Không thể rời voice.",
                    ephemeral=True
                )

        except Exception:
            await interaction.response.send_message(
                "Có lỗi xảy ra khi rời voice.",
                ephemeral=True
            )

    # =========================
    # STATUS
    # =========================
    @app_commands.command(name="vstatus")
    async def vstatus(self, interaction: discord.Interaction):
        try:
            vc = interaction.guild.voice_client

            if not vc or not vc.is_connected():
                return await interaction.response.send_message(
                    "Bot hiện không ở voice."
                )

            await interaction.response.send_message(
                f"Đang ở: {vc.channel.name}"
            )

        except Exception:
            await interaction.response.send_message(
                "Không thể lấy trạng thái voice.",
                ephemeral=True
            )


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceSystem(bot))
