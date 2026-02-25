import discord
from discord import app_commands
from discord.ext import commands

from core.embed_ui import EmbedBuilderView
from core.embed_storage import load_embed, delete_embed


class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="embed",
            description="Embed management"
        )

    @app_commands.command(
        name="create",
        description="Create new embed"
    )
    async def create(self, interaction: discord.Interaction, name: str):

        embed = discord.Embed(
            title="New Embed",
            description="Edit using buttons below.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=EmbedBuilderView(name)
        )

    @app_commands.command(
        name="show",
        description="Show embed"
    )
    async def show(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                "❌ Embed not found."
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

    @app_commands.command(
        name="edit",
        description="Edit embed"
    )
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                "❌ Embed not found."
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
            view=EmbedBuilderView(name)
        )

    @app_commands.command(
        name="delete",
        description="Delete embed"
    )
    async def delete(self, interaction: discord.Interaction, name: str):

        if delete_embed(name):
            await interaction.response.send_message(
                f"🗑 Embed `{name}` deleted."
            )
        else:
            await interaction.response.send_message(
                "❌ Embed not found."
            )


class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="p",
            description="Main command group"
        )

        self.add_command(EmbedGroup())


class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.add_command(PGroup())


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
