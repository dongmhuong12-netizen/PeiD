import discord
from discord import app_commands
from discord.ext import commands


class Root(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    p = app_commands.Group(
        name="p",
        description="Main command group",
        default_permissions=discord.Permissions(manage_guild=True)
    )


async def setup(bot):
    await bot.add_cog(Root(bot))
