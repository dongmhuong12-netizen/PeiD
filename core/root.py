import discord
from discord import app_commands
from discord.ext import commands


class Root(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Root group
        self.p = app_commands.Group(
            name="p",
            description="Main command group",
            default_permissions=discord.Permissions(manage_guild=True)
        )

        # Subgroup embed
        self.embed = app_commands.Group(
            name="embed",
            description="Embed management"
        )

        self.p.add_command(self.embed)
        self.bot.tree.add_command(self.p)


async def setup(bot):
    await bot.add_cog(Root(bot))
