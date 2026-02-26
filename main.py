import discord
from discord.ext import commands
import asyncio

TOKEN = "YOUR_BOT_TOKEN_HERE"  # <-- thay token

intents = discord.Intents.default()
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
        await bot.load_extension("core.root")  # đúng tên folder bạn nói
        await bot.start(TOKEN)


asyncio.run(main())
