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
# IMPORT COMMAND MODULES
# ==============================

def load_command_modules():
    if os.path.isdir("./commands"):
        for root, dirs, files in os.walk("./commands"):
            for file in files:
                if file.endswith(".py"):
                    module_path = (
                        os.path.join(root, file)
                        .replace("./", "")
                        .replace("/", ".")
                        .replace(".py", "")
                    )
                    try:
                        __import__(module_path)
                        logger.info(f"Imported module: {module_path}")
                    except Exception:
                        logger.exception(f"Failed to import: {module_path}")
    else:
        logger.warning("commands folder not found.")

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

    load_command_modules()

    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
