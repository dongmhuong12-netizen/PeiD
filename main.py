import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.voice_manager import VoiceManager
from core.voice_service import VoiceService
from core.voice_listener import VoiceListener


os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")


# WEB
async def run_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    while True:
        await asyncio.sleep(3600)


# BOT
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = commands.AutoShardedBot(
    command_prefix="!",
    intents=intents
)


# EXTENSIONS
EXTENSIONS = [
    "commands.voice_system",
    "core.voice_listener"
]


async def load_extensions():
    for ext in EXTENSIONS:
        await bot.load_extension(ext)


@bot.event
async def on_ready():
    print("BOT READY")

    await bot.tree.sync()

    bot.loop.create_task(VoiceService(bot).start())


async def main():
    # IMPORTANT ORDER FIX
    bot.voice_manager = VoiceManager(bot)

    await load_extensions()

    await asyncio.gather(
        run_web_server(),
        bot.start(TOKEN)
    )


if __name__ == "__main__":
    asyncio.run(main())
