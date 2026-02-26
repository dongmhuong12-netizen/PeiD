import os
import sys

# Thêm thư mục gốc project vào Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import discord
from discord.ext import commands
import asyncio

TOKEN = "YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"Sync error: {e}")


async def main():
    async with bot:
        await bot.load_extension("core.root")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
