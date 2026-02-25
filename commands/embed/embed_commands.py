import discord
from discord import app_commands
from discord.ext import commands

from systems.embed.manager import EmbedManager


class EmbedCommands(commands.GroupCog, name="p"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = EmbedManager(bot.db)

    @app_commands.command(name="embed_create", description="Tạo một embed mới")
    @app_commands.describe(name="Tên embed")
    async def embed_create(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh chỉ dùng trong server.",
                ephemeral=True
            )
            return

        try:
            await self.manager.create_embed(interaction.guild.id, name)

            await interaction.response.send_message(
                f"Đã tạo embed `{name}` thành công.",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.response.send_message(
                str(e),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCommands(bot))
