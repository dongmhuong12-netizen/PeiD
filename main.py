import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

async def load_extensions():
    await bot.load_extension("booster")           # V1
    await bot.load_extension("boost_system_v2")   # V2

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()  # sync global cho V2
        print("Slash commands synced.")
    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Bot online: {bot.user}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
