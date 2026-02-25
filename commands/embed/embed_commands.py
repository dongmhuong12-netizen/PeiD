import discord
from discord import app_commands
from discord.ext import commands

from systems.embed.manager import EmbedManager
from systems.embed.view import EmbedEditorView


class PCommands(commands.GroupCog, name="p"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = EmbedManager(bot.db)

    # Subgroup: /p embed
    embed = app_commands.Group(
        name="embed",
        description="Quản lý embed"
    )

    # Command: /p embed create
    @embed.command(name="create", description="Tạo một embed mới")
    @app_commands.describe(name="Tên embed")
    async def create(
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
            # Lưu vào database
            await self.manager.create_embed(interaction.guild.id, name)

            # Dữ liệu embed ban đầu
            embed_data = {
                "title": name,
                "description": "Chưa có mô tả",
                "color": 0x2F3136
            }

            # Tạo editor view
            view = EmbedEditorView(embed_data)

            # Gửi preview + UI
            await interaction.response.send_message(
                embed=view.build_embed(),
                view=view
            )

        except ValueError as e:
            await interaction.response.send_message(
                str(e),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PCommands(bot))
