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

# =========================
# WEB SERVER
# =========================
async def health(request):
    return web.Response(text="Bot is running")


async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    while True:
        await asyncio.sleep(3600)


# =========================
# BOT
# =========================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.AutoShardedBot(
    command_prefix=commands.when_mentioned,
    intents=intents
)


# =========================
# ATTACH CORE
# =========================
bot.voice_manager = VoiceManager(bot)


# =========================
# EXTENSIONS
# =========================
EXTENSIONS = [
    "commands.voice_system",
    "core.voice_listener"
]


async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Failed {ext}: {repr(e)}")


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        await bot.tree.sync()
    except:
        pass

    bot.loop.create_task(VoiceService(bot).start())


# =========================
# MAIN
# =========================
async def main():
    await load_extensions()

    await asyncio.gather(
        run_web_server(),
        bot.start(TOKEN)
    )


if __name__ == "__main__":
    asyncio.run(main())
