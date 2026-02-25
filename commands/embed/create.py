import discord
from discord.ext import commands
from systems.embed_system import EmbedSystem
from storage.embed_storage import EmbedStorage


class EmbedCreate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="create",
        description="Create a new embed"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str
    ):

        success, error = EmbedSystem.create_embed(
            interaction.guild_id,
            name
        )

        if not success:

            if error == "INVALID_NAME":
                await interaction.response.send_message(
                    "❌ Invalid name.",
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
                    "❌ Limit reached (15).",
                    ephemeral=True
                )
                return

        embed_data = EmbedStorage.get_guild(interaction.guild_id)[name]

        preview = discord.Embed(
            color=int(embed_data["color"], 16)
        )

        preview.add_field(
            name="Status",
            value="Title: ❌\nDescription: ❌\nImage: ❌",
            inline=False
        )

        await interaction.response.send_message(
            "✅ Embed created.",
            embed=preview,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(EmbedCreate(bot))
