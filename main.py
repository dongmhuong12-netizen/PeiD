import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.voice_manager import VoiceManager
from systems.voice_recovery import VoiceRecovery

os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")

# =========================
# WEB SERVER (KEEP ALIVE)
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
# INTENTS
# =========================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True
intents.voice_states = True  # 🔥 IMPORTANT

bot = commands.AutoShardedBot(
    command_prefix=commands.when_mentioned,
    intents=intents
)

# =========================
# EXTENSIONS
# =========================
EXTENSIONS = [
    "core.root",
    "systems.reaction_role",
    "commands.voice_system"
]

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}", flush=True)
        except Exception as e:
            print(f"Failed {ext}: {repr(e)}", flush=True)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}", flush=True)

    # 🔥 stabilize gateway
    await asyncio.sleep(8)

    try:
        await bot.tree.sync()
    except:
        pass

    # 🔥 start recovery watchdog
    bot.loop.create_task(VoiceRecovery(bot).start())

# =========================
# MAIN
# =========================
async def main():
    # 🔥 stabilize boot
    await asyncio.sleep(5)

    bot.voice_manager = VoiceManager(bot)

    await load_extensions()

    await asyncio.gather(
        run_web_server(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    asyncio.run(main())
