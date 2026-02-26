import os
import asyncio
import logging
import discord
from discord.ext import commands

# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("bot")

print("APP STARTING...")

# ==============================
# INTENTS
# ==============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ==============================
# BOT SETUP
# ==============================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ==============================
# SYNC SLASH COMMANDS
# ==============================

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        logger.info("Slash commands synced globally.")
    except Exception:
        logger.exception("Failed to sync slash commands.")

    logger.info(f"Bot is ready. Logged in as {bot.user}")

# ==============================
# LOAD COGS (safe)
# ==============================

async def load_extensions():
    if not os.path.isdir("./cogs"):
        logger.info("No cogs folder found, skipping extension loading.")
        return

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded extension: {filename}")
            except Exception:
                logger.exception(f"Failed to load extension: {filename}")

# ==============================
# MAIN
# ==============================

async def main():
    token = os.getenv("TOKEN")

    if not token:
        logger.error("TOKEN environment variable not found.")
        return

    async with bot:
        await load_extensions()
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
