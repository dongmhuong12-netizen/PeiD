import discord
from discord.ext import commands


class Root(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Main command: /p
        self.p = discord.app_commands.Group(
            name="p",
            description="Main command group"
        )

        # Sub group: /p embed
        self.embed = discord.app_commands.Group(
            name="embed",
            description="Embed management",
            parent=self.p
        )

        # Register root group
        self.bot.tree.add_command(self.p)


async def setup(bot):
    await bot.add_cog(Root(bot))
