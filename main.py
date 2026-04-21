import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.voice_manager import VoiceManager
from core.voice_service import VoiceService
from core.state import State  # 🔥 CORE MEMORY LAYER

os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")

# =========================
# WEB SERVER (RENDER KEEP ALIVE)
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

    print(f"[WEB] Running on port {port}", flush=True)

    while True:
        await asyncio.sleep(3600)

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True
intents.voice_states = True

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
    "commands.voice_system",
    "core.voice_listener",
]

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"[LOAD] {ext}", flush=True)
        except Exception as e:
            print(f"[ERROR LOAD] {ext}: {e}", flush=True)

# =========================
# READY STATE (PREMIUM BOOT LOGIC)
# =========================

bot._ready_once = False

@bot.event
async def on_ready():
    if bot._ready_once:
        print("[RECONNECT] Bot reconnected", flush=True)
        return

    bot._ready_once = True

    # =========================
    # SLASH SYNC
    # =========================
    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] Synced: {len(synced)}", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"[READY] Logged in as {bot.user} ({bot.user.id})", flush=True)

    # =========================
    # 🔥 WAKE SAFE CORE RESTORE (IMPORTANT)
    # =========================
    await State.resync()

    print("[STATE] Resynced successfully", flush=True)

    # =========================
    # SERVICES START
    # =========================
    bot.loop.create_task(VoiceService(bot).start())

    print("[SERVICE] VoiceService started", flush=True)

# =========================
# MAIN ENTRY
# =========================

async def main():
    bot.voice_manager = VoiceManager(bot)

    await load_extensions()

    await asyncio.gather(
        run_web_server(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    asyncio.run(main())
