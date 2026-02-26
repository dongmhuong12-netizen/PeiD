import os
import asyncio
import logging
import discord
from discord.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==============================
# READY
# ==============================

@bot.event
async def on_ready():
    logger.info(f"Bot is ready. Logged in as {bot.user}")

# ==============================
# MAIN
# ==============================

async def main():
    token = os.getenv("TOKEN")

    if not token:
        logger.error("TOKEN environment variable not found.")
        return

    async with bot:
        # 🔥 LOAD ROOT COG (QUAN TRỌNG)
        await bot.load_extension("core.root")

        # 🔥 SYNC COMMAND TREE
        await bot.tree.sync()

        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
