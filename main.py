import os
import sys

# Thêm thư mục gốc project vào Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import discord
from discord.ext import commands
import asyncio

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=1475879071857508393
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    # Sync sau khi bot đã ready
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"Sync error: {e}")


async def main():
    async with bot:
        # Load extension trước khi start
        await bot.load_extension("core.root")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
