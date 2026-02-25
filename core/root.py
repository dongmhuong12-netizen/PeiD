from discord import app_commands
from core.embed_ui import EmbedBuilderView
from core.embed_storage import load_embed, delete_embed


class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Embed management")

    @app_commands.command(name="create", description="Create new embed")
    async def create(self, interaction: discord.Interaction, name: str):

        embed = discord.Embed(
            title="New Embed",
            description="Edit using buttons below.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=EmbedBuilderView(name),
            ephemeral=True
        )

    @app_commands.command(name="show", description="Show embed")
    async def show(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                "❌ Embed not found.",
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

    @app_commands.command(name="edit", description="Edit embed")
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                "❌ Embed not found.",
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
            view=EmbedBuilderView(name),
            ephemeral=True
        )

    @app_commands.command(name="delete", description="Delete embed")
    async def delete(self, interaction: discord.Interaction, name: str):

        if delete_embed(name):
            await interaction.response.send_message(
                f"🗑 Embed `{name}` deleted.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Embed not found.",
                ephemeral=True
            )
