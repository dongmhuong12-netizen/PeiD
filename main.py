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

synced = False  # đảm bảo sync 1 lần duy nhất

@bot.event
async def on_ready():
    global synced

    logger.info(f"Bot is ready. Logged in as {bot.user}")

    if not synced:
        try:
            await bot.tree.sync()
            logger.info("Slash commands synced successfully.")
            synced = True
        except Exception as e:
            logger.exception("Slash command sync failed.")

async def main():
    token = os.getenv("TOKEN")

    if not token:
        logger.error("TOKEN environment variable not found.")
        return

    async with bot:
        # Load Root Cog (đây là nơi đăng ký /p)
        await bot.load_extension("core.root")

        # KHÔNG sync ở đây nữa
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
