import discord
from discord.ext import commands


class Root(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # /p
        self.p = discord.app_commands.Group(
            name="p",
            description="Main command group"
        )

        # /p embed
        self.embed = discord.app_commands.Group(
            name="embed",
            description="Embed management",
            parent=self.p
        )

    async def cog_load(self):
        # Register root group safely
        try:
            self.bot.tree.add_command(self.p)
        except discord.app_commands.CommandAlreadyRegistered:
            pass


async def setup(bot):
    await bot.add_cog(Root(bot))
