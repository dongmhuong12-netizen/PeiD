import discord
from discord.ext import commands
from .core import EditV2
from .database import Database

async def setup(bot: commands.Bot):
    db = Database()
    await db.initialize()

    await bot.add_cog(EditV2(bot, db))
