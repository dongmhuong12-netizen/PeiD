import discord
from discord import app_commands
from discord.ext import commands

from core.embed_ui import EmbedBuilderView
from core.embed_storage import load_embed


# ===== Embed Subgroup =====
class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="embed",
            description="Embed management"
        )

    # /p embed create
    @app_commands.command(
        name="create",
        description="Create new embed"
    )
    async def create(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="New Embed",
            description="Edit using buttons below.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=EmbedBuilderView(),
            ephemeral=True
        )

    # /p embed show
    @app_commands.command(
        name="show",
        description="Show saved embed"
    )
    async def show(self, interaction: discord.Interaction):

        data = load_embed()

        if not data:
            await interaction.response.send_message(
                "❌ No saved embed found.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color")
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        await interaction.response.send_message(embed=embed)

    # /p embed edit
    @app_commands.command(
        name="edit",
        description="Edit saved embed"
    )
    async def edit(self, interaction: discord.Interaction):

        data = load_embed()

        if not data:
            await interaction.response.send_message(
                "❌ No saved embed to edit.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color")
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        await interaction.response.send_message(
            embed=embed,
            view=EmbedBuilderView(),
            ephemeral=True
        )


# ===== Root Group (/p) =====
class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="p",
            description="Main command group"
        )

        self.add_command(EmbedGroup())


# ===== Root Cog =====
class Root(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.add_command(PGroup())


async def setup(bot):
    await bot.add_cog(Root(bot))
