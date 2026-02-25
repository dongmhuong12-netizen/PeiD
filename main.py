import discord
from discord.ext import commands
import asyncio


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def main():
    async with bot:
        await bot.load_extension("core.root")
        await bot.load_extension("commands.embed.embed_group")
        await bot.load_extension("commands.embed.create")
        await bot.start("YOUR_TOKEN")


asyncio.run(main())
