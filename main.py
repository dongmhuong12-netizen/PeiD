import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

class PeiBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load cogs
        await self.load_extension("booster_v1")
        await self.load_extension("booster_v2")

        # Sync global (V2)
        await self.tree.sync()

        # Sync riêng guild V1
        guild = discord.Object(id=1111391147030482944)
        await self.tree.sync(guild=guild)

bot = PeiBot()

async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
