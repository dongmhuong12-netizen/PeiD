import discord
from discord import app_commands
from discord.ext import commands


class VoiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = bot.voice_manager

    @app_commands.command(name="vjoin")
    async def vjoin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.voice:
            return await interaction.followup.send("Bạn chưa ở voice.")

        result = await self.manager.connect(
            interaction.guild,
            interaction.user.voice.channel
        )

        if result is True:
            return await interaction.followup.send("Đã vào voice.")

        return await interaction.followup.send(f"Lỗi voice: {result}")

    @app_commands.command(name="vleave")
    async def vleave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        result = await self.manager.disconnect(interaction.guild)

        if result is True:
            return await interaction.followup.send("Đã rời voice.")

        return await interaction.followup.send(f"Lỗi: {result}")

    @app_commands.command(name="vstatus")
    async def vstatus(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client

        if not vc:
            return await interaction.response.send_message("Bot không ở voice.")

        await interaction.response.send_message(f"Đang ở: {vc.channel.name}")


async def setup(bot):
    await bot.add_cog(VoiceSystem(bot))
