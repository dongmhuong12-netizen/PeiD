import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# LOAD EXTENSIONS
# =========================

async def load_extensions():
    await bot.load_extension("core.root")


# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    try:
        # ❌ KHÔNG clear
        # ❌ KHÔNG guild sync
        # ✅ Global sync chuẩn

        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global commands.")

    except Exception as e:
        print(f"Sync error: {e}")


# =========================
# START BOT
# =========================

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


asyncio.run(main())
