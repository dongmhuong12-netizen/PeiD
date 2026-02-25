import discord
from discord.ext import commands


class Root(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.p = discord.app_commands.Group(
            name="p",
            description="Main command group"
        )

        self.embed = discord.app_commands.Group(
            name="embed",
            description="Embed management"
        )

        self.p.add_command(self.embed)

    async def cog_load(self):
        # chỉ add khi cog load xong
        try:
            self.bot.tree.add_command(self.p)
        except discord.app_commands.CommandAlreadyRegistered:
            pass


async def setup(bot):
    await bot.add_cog(Root(bot))
