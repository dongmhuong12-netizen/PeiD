import os
import logging
import discord
from discord.ext import commands

# =========================
# LOGGING CONFIG
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("bot")

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    logger.info(f"Bot online: {bot.user} (ID: {bot.user.id})")
    logger.info("Bot is ready and connected to Discord.")

@bot.event
async def on_disconnect():
    logger.warning("Bot disconnected from Discord.")

@bot.event
async def on_resumed():
    logger.info("Bot connection resumed.")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"Unhandled error in event: {event}")

# =========================
# GLOBAL ERROR HANDLER
# =========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    logger.exception(f"Slash command error: {error}")

    if interaction.response.is_done():
        await interaction.followup.send("Đã xảy ra lỗi khi thực thi lệnh.", ephemeral=True)
    else:
        await interaction.response.send_message("Đã xảy ra lỗi khi thực thi lệnh.", ephemeral=True)

# =========================
# LOAD COGS (nếu có)
# =========================

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded extension: {filename}")
            except Exception as e:
                logger.exception(f"Failed to load extension {filename}: {e}")

# =========================
# MAIN START
# =========================

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
