import discord
from discord import app_commands
from discord.ext import commands


class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="p",
            description="Main command group"
        )


p_group = PGroup()


class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
    bot.tree.add_command(p_group)
