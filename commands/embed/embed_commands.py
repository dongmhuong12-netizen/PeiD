import discord
from discord import app_commands
from discord.ext import commands

from systems.embed.manager import EmbedManager
from systems.embed.view import EmbedEditorView


class EmbedCommands(commands.GroupCog, name="p"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = EmbedManager()

    embed = app_commands.Group(
        name="embed",
        description="Quản lý embed"
    )

    # /p embed create
    @embed.command(name="create", description="Tạo embed mới")
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

        await self.manager.create_embed(
            embed_id=name,
            title="New Embed",
            description="Chỉnh sửa nội dung sau.",
        )

        await interaction.response.send_message(
            f"✅ Đã tạo embed `{name}`",
            ephemeral=True
        )

    # /p embed show
    @embed.command(name="show", description="Hiển thị embed")
    async def show(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        data = await self.manager.get_embed(name)

        if not data:
            await interaction.response.send_message(
                "❌ Không tìm thấy embed.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=data["color"]
        )

        if data["image_url"]:
            embed.set_image(url=data["image_url"])

        await interaction.response.send_message(embed=embed)

    # /p embed delete
    @embed.command(name="delete", description="Xóa embed")
    async def delete(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        success = await self.manager.delete_embed(name)

        if not success:
            await interaction.response.send_message(
                "❌ Không tìm thấy embed.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🗑 Đã xóa embed `{name}`",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCommands(bot))
