import discord
from discord.ext import commands
from discord import app_commands  # ✅ FIX LỖI NameError

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

        # 🔥 Nếu đã có UI cùng tên → xoá UI cũ trước
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
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

        await interaction.response.send_message(
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
                "❌ Embed not found.",
                ephemeral=True
            )
            return

        # 🔥 Nếu đã có UI cùng tên → xoá UI cũ trước
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
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

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

    # -------------------------
    # DELETE
    # -------------------------
    @app_commands.command(name="delete", description="Delete embed UI and storage")
    async def delete(self, interaction: discord.Interaction, name: str):

        # Xoá storage
        delete_embed(name)

        # 🔥 Xoá toàn bộ UI đang mở có cùng tên
        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        await interaction.response.send_message(
            f"🗑 Embed `{name}` UI deleted everywhere.",
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
# COG LOADER
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.add_command(PGroup())


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
