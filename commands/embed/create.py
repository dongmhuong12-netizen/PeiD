import discord
from discord.ext import commands
from core.root import Root


class EmbedCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        root: Root = bot.get_cog("Root")
        root.embed.add_command(self.create)

    @discord.app_commands.command(
        name="create",
        description="Create a new embed"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        await interaction.response.send_message(
            f"✅ Embed `{name}` created.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(EmbedCreate(bot))
