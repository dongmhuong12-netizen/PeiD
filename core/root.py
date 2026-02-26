import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
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

        # Nếu có UI cùng tên đang mở → đóng ngay
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        existing = load_embed(name)
        if existing:
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`. "
                f"Nếu tạo embed mà không tìm thấy, thử tìm embed đó bằng cách dùng lệnh /p embed edit.",
                ephemeral=True
            )
            return

        embed_data = {
            "title": "New Embed",
            "description": "Edit using buttons below.",
            "color": 0x5865F2
        }

        view = EmbedUIView(name, embed_data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=f"Đã tạo embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

    # -------------------------
    # EDIT
    # -------------------------
    @app_commands.command(name="edit", description="Edit existing embed")
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không tìm thấy.",
                ephemeral=True
            )
            return

        # Đóng tất cả UI cũ của embed này
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        view = EmbedUIView(name, data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=f"Bạn đang chỉnh sửa embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

    # -------------------------
    # DELETE
    # -------------------------
    @app_commands.command(name="delete", description="Delete embed")
    async def delete(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể dùng lệnh.",
                ephemeral=True
            )
            return

        # Đóng tất cả UI đang mở
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        delete_embed(name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá vĩnh viễn, có thể tạo embed mới bằng tên của embed này.",
            ephemeral=True
        )

    # -------------------------
    # SHOW
    # -------------------------
    @app_commands.command(name="show", description="Send embed to channel")
    async def show(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể gửi.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color", 0x2F3136)
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message(
            f"Embed `{name}` đã được gửi.",
            ephemeral=True
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
