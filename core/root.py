import discord
from discord import app_commands
from discord.ext import commands


class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="embed",
            description="Embed management"
        )

    @app_commands.command(
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


class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="p",
            description="Main command group"
        )

        self.add_command(EmbedGroup())


class Root(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.add_command(PGroup())


async def setup(bot):
    await bot.add_cog(Root(bot))
