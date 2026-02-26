import discord
from discord import app_commands
from discord.ext import commands

from core.embed_storage import (
    save_embed,
    load_embed,
    delete_embed,
    embed_exists
)

from core.ui import EmbedUIView


class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =========================
    # GROUP CHA /p
    # =========================
    p = app_commands.Group(name="p", description="Panel commands")

    # =========================
    # SUBGROUP /p embed
    # =========================
    embed = app_commands.Group(
        name="embed",
        description="Embed management",
        parent=p
    )

    # =========================
    # CREATE
    # =========================
    @embed.command(name="create", description="Tạo embed mới")
    async def create(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if embed_exists(name):
            await interaction.response.send_message(
                f"Đã có embed `{name}` tồn tại.",
                ephemeral=True
            )
            return

        embed_data = {
            "title": f"Embed: {name}",
            "description": "Embed mới được tạo. Hãy chỉnh sửa nội dung.",
            "color": 0x5865F2
        }

        embed = discord.Embed(
            title=embed_data["title"],
            description=embed_data["description"],
            color=embed_data["color"]
        )

        view = EmbedUIView(name, embed_data)

        msg = await interaction.response.send_message(
            f"Đã tạo embed `{name}`",
            embed=embed,
            view=view
        )

    # =========================
    # EDIT
    # =========================
    @embed.command(name="edit", description="Chỉnh sửa embed")
    async def edit(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not embed_exists(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        embed_data = load_embed(name)

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            color=embed_data.get("color", 0x5865F2)
        )

        if embed_data.get("image"):
            embed.set_image(url=embed_data["image"])

        view = EmbedUIView(name, embed_data)

        await interaction.response.send_message(
            f"Đang chỉnh sửa embed `{name}`",
            embed=embed,
            view=view
        )

    # =========================
    # DELETE
    # =========================
    @embed.command(name="delete", description="Xoá embed")
    async def delete(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not embed_exists(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        delete_embed(name)

        await interaction.response.send_message(
            f"Đã xoá embed `{name}`.",
            ephemeral=True
        )

    # =========================
    # SHOW
    # =========================
    @embed.command(name="show", description="Hiển thị embed")
    async def show(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not embed_exists(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        embed_data = load_embed(name)

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            color=embed_data.get("color", 0x5865F2)
        )

        if embed_data.get("image"):
            embed.set_image(url=embed_data["image"])

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
