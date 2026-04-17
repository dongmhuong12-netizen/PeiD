import discord
from discord import app_commands
from discord.ext import commands


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
            await interaction.response.defer(ephemeral=True)

            if not interaction.user.voice or not interaction.user.voice.channel:
                return await interaction.followup.send("Bạn chưa ở voice channel.")

            result = await self.manager.join(
                interaction,
                interaction.user.voice.channel
            )

            if result is True:
                return await interaction.followup.send("Đã vào voice.")

            if result == "COOLDOWN":
                return await interaction.followup.send("Đang thao tác quá nhanh, thử lại sau.")

            await interaction.followup.send(f"Không thể join voice: `{result}`")

        except Exception as e:
            print("[VJOIN ERROR]:", repr(e))
            await interaction.followup.send("Lỗi xử lý lệnh vjoin.")

    # =========================
    # LEAVE
    # =========================
    @app_commands.command(name="vleave")
    async def vleave(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            result = await self.manager.leave(interaction.guild)

            if result is True:
                return await interaction.followup.send("Đã rời voice.")

            await interaction.followup.send(f"Lỗi leave voice: `{result}`")

        except Exception as e:
            print("[VLEAVE ERROR]:", repr(e))
            await interaction.followup.send("Lỗi xử lý vleave.")

    # =========================
    # STATUS
    # =========================
    @app_commands.command(name="vstatus")
    async def vstatus(self, interaction: discord.Interaction):
        try:
            vc = interaction.guild.voice_client

            if not vc or not vc.is_connected():
                return await interaction.response.send_message("Bot không ở voice.")

            await interaction.response.send_message(
                f"Đang ở voice: {vc.channel.name}"
            )

        except Exception as e:
            print("[VSTATUS ERROR]:", repr(e))
            await interaction.response.send_message("Không lấy được trạng thái.")


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceSystem(bot))
