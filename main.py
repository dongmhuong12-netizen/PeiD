import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

# ===== VOICE IMPORT =====
from core.voice_manager import VoiceManager
from systems.voice_recovery import VoiceRecovery


os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")


# =========================
# WEB SERVER FOR RENDER
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

    print(f"Web server running on port {port}", flush=True)

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

bot = commands.AutoShardedBot(
    command_prefix=commands.when_mentioned,
    intents=intents
)


# =========================
# VOICE ATTACH (NEW)
# =========================

bot.voice_manager = VoiceManager(bot)


# =========================
# EXTENSIONS
# =========================

EXTENSIONS = [
    "core.root",
    "systems.reaction_role",

    # ===== VOICE SYSTEM =====
    "commands.voice_system"
]


async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}", flush=True)
        except Exception as e:
            print(f"Failed to load {ext}: {e}", flush=True)


# =========================
# READY (FIXED STABLE SYNC)
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})", flush=True)
    print("Bot ready", flush=True)

    try:
        # đảm bảo bot tree đã sẵn sàng trước khi sync
        await bot.wait_until_ready()

        synced = await bot.tree.sync()
        print(f"Slash synced: {len(synced)}", flush=True)

    except Exception as e:
        print(f"Slash sync failed: {e}", flush=True)

    # ===== VOICE RECOVERY START =====
    bot.loop.create_task(VoiceRecovery(bot).start())


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
