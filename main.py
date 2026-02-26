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
# READY EVENT
# ==============================

@bot.event
async def on_ready():
    logger.info(f"Bot is ready. Logged in as {bot.user}")

# ==============================
# LOAD EXTENSIONS (LOAD COMMANDS FOLDER)
# ==============================

async def load_extensions():

    # Load commands folder
    if os.path.isdir("./commands"):
        for filename in os.listdir("./commands"):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"commands.{filename[:-3]}")
                    logger.info(f"Loaded command: {filename}")
                except Exception:
                    logger.exception(f"Failed to load command: {filename}")

    else:
        logger.warning("commands folder not found.")

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
