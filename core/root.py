import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView
from core.embed_storage import load_embed, delete_embed

# Track active views
ACTIVE_VIEWS = {}


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
                f"Đã có embed tồn tại với tên `{name}`."
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
            content=f"Đã tạo embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message
        ACTIVE_VIEWS[name] = view

    # -------------------------
    # EDIT
    # -------------------------
    @app_commands.command(name="edit", description="Open embed UI to edit existing embed")
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không tìm thấy."
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
            content=f"Bạn đang chỉnh sửa embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message
        ACTIVE_VIEWS[name] = view

    # -------------------------
    # DELETE
    # -------------------------
    @app_commands.command(name="delete", description="Delete saved embed")
    async def delete(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể dùng lệnh."
            )
            return

        # Nếu UI đang mở → disable nó
        if name in ACTIVE_VIEWS:
            view = ACTIVE_VIEWS[name]

            try:
                if view.message:
                    await view.message.edit(view=None)
            except:
                pass

            view.stop()
            del ACTIVE_VIEWS[name]

        delete_embed(name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá hoàn toàn."
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
