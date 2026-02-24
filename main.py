import discord
from discord.ext import commands
import os
import asyncio

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("booster")
        await bot.load_extension("boost_system_v2")
        await bot.start(TOKEN)


asyncio.run(main())
