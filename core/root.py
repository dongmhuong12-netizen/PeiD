import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView
from core.embed_storage import load_embed, delete_embed


# =============================
# EMBED SUBGROUP
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Embed management commands")

    # -------------------------
    # CREATE
    # -------------------------
    @app_commands.command(name="create", description="Create a new embed UI")
    async def create(self, interaction: discord.Interaction, name: str):

        existing_data = load_embed(name)
        if existing_data:
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`.\n\n"
                "• Không thể tạo embed mới với tên này.\n"
                "• Vui lòng sử dụng tên khác.\n"
                "• Hoặc dùng `/p embed edit` để chỉnh sửa embed đã tồn tại."
            )
            return

        embed_data = {
            "title": "New Embed",
            "description": "Edit using buttons below.",
            "color": 0x5865F2
        }

        embed = discord.Embed(
            title=embed_data["title"],
            description=embed_data["description"],
            color=embed_data["color"]
        )

        view = EmbedUIView(name, embed_data)

        await interaction.response.send_message(
            content=(
                f"Đã tạo embed với tên `{name}`.\n\n"
                "• Bạn có thể chỉnh sửa embed bằng các nút bên dưới.\n"
                "• Hãy Save sau khi chỉnh sửa.\n"
                "• Nếu không Save, embed sẽ không được lưu."
            ),
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

    # -------------------------
    # EDIT
    # -------------------------
    @app_commands.command(name="edit", description="Open embed UI to edit existing embed")
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại."
            )
            return

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color")
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        view = EmbedUIView(name, data)

        await interaction.response.send_message(
            content=(
                f"Bạn đang chỉnh sửa embed `{name}`.\n\n"
                "• Sau khi chỉnh sửa, hãy Save để cập nhật.\n"
                "• Nếu thoát mà chưa Save, thay đổi sẽ không được lưu."
            ),
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

    # -------------------------
    # DELETE
    # -------------------------
    @app_commands.command(name="delete", description="Delete saved embed")
    async def delete(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại."
            )
            return

        delete_embed(name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá vĩnh viễn, có thể tạo lại embed mới với tên này."
        )

    # -------------------------
    # SHOW
    # -------------------------
    @app_commands.command(name="show", description="Send saved embed to this channel")
    async def show(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                "Embed không tồn tại."
            )
            return

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color")
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        await interaction.channel.send(embed=embed)

        await interaction.response.send_message(
            f"Embed `{name}` đã được gửi."
        )


# =============================
# MAIN /p GROUP
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="Main command group")
        self.add_command(EmbedGroup())


# =============================
# COG
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.add_command(PGroup())


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
