import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedBuilderView, ACTIVE_EMBED_VIEWS
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
            system_message = (
                f"Đã có embed tồn tại với tên `{name}`.\n\n"
                "• Không thể tạo embed mới với tên này.\n"
                "• Vui lòng sử dụng tên khác.\n"
                "• Hoặc dùng `/p embed edit` để chỉnh sửa embed đã tồn tại."
            )

            await interaction.response.send_message(
                content=system_message
            )
            return

        # Nếu chỉ là draft UI chưa save -> đóng UI cũ
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.edit(view=None)
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        embed = discord.Embed(
            title="New Embed",
            description="Edit using buttons below.",
            color=discord.Color.blurple()
        )

        view = EmbedBuilderView(name)

        system_message = (
            f"Đã tạo embed với tên `{name}`.\n\n"
            "• Bạn có thể sử dụng embed này để tạo tin nhắn chào mừng, rời đi\n"
            "  hoặc các banner hệ thống khi dùng lệnh `/p embed show`.\n"
            "• Lưu ý: hãy Save sau khi chỉnh sửa. Nếu không embed sẽ không được lưu lại\n"
            "  hoặc sẽ bị coi là không tồn tại.\n"
            "• Nếu có thắc mắc, dùng lệnh `/help` hoặc tham gia server hỗ trợ."
        )

        await interaction.response.send_message(
            content=system_message,
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
                f"Embed `{name}` không tồn tại, không thể tìm."
            )
            return

        # Đóng UI cũ nếu đang mở
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.edit(view=None)
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color")
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        view = EmbedBuilderView(name, existing_data=data)

        system_message = (
            f"Bạn đang chỉnh sửa embed `{name}`.\n\n"
            "• Sau khi chỉnh sửa, hãy Save để cập nhật thay đổi.\n"
            "• Nếu thoát mà chưa save, thay đổi sẽ không được lưu lại.\n"
            "• Dùng `/p embed show` để gửi embed này vào kênh."
        )

        await interaction.response.send_message(
            content=system_message,
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

    # -------------------------
    # DELETE
    # -------------------------
    @app_commands.command(name="delete", description="Delete embed UI and storage")
    async def delete(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại, không thể dùng lệnh."
            )
            return

        delete_embed(name)

        # Xoá UI nếu đang mở
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.edit(view=None)
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

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
