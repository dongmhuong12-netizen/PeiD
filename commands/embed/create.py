import discord
from discord.ext import commands
from commands.embed.embed_group import embed_group
from systems.embed_system import EmbedSystem
from storage.embed_storage import EmbedStorage


class EmbedCreate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @embed_group.command(name="create", description="Create a new embed")
    async def create(self, interaction: discord.Interaction, name: str):

        success, error = EmbedSystem.create_embed(interaction.guild_id, name)

        if not success:

            if error == "INVALID_NAME":
                await interaction.response.send_message(
                    "❌ Invalid name. Use A-Z 0-9 _ - (max 32).",
                    ephemeral=True
                )
                return

            if error == "EXISTS":
                await interaction.response.send_message(
                    "❌ Embed already exists.",
                    ephemeral=True
                )
                return

            if error == "LIMIT":
                await interaction.response.send_message(
                    "❌ You reached the limit (15 embeds).",
                    ephemeral=True
                )
                return

        embed_data = EmbedStorage.get_guild(interaction.guild_id)[name]

        preview = discord.Embed(
            title=None,
            description=None,
            color=int(embed_data["color"], 16)
        )

        status = (
            "Title: ❌\n"
            "Description: ❌\n"
            f"Color: {embed_data['color']}\n"
            "Image: ❌"
        )

        preview.add_field(name="Embed Status", value=status, inline=False)
        preview.set_footer(text=f"Embed name: {name}")

        await interaction.response.send_message(
            "✅ Embed created.",
            embed=preview,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(EmbedCreate(bot))
