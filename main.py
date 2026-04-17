import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

# ===== VOICE IMPORT =====
from core.voice_manager import VoiceManager
from core.voice_service import VoiceService
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


# =========================
# BOT CLASS (FIX IMPORTANT)
# =========================

class MyBot(commands.AutoShardedBot):
    async def setup_hook(self):
        # voice system init đúng lifecycle
        self.voice_manager = VoiceManager(self)
        self.loop.create_task(VoiceService(self).start())
        self.loop.create_task(VoiceRecovery(self).start())

        # load extensions
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}", flush=True)
            except Exception as e:
                print(f"Failed to load {ext}: {e}", flush=True)

        # sync slash sau khi system ready
        try:
            synced = await self.tree.sync()
            print(f"Slash synced: {len(synced)}", flush=True)
        except Exception as e:
            print(f"Slash sync failed: {e}", flush=True)


bot = MyBot(
    command_prefix=commands.when_mentioned,
    intents=intents
)


# =========================
# EXTENSIONS LIST
# =========================

EXTENSIONS = [
    "core.root",
    "systems.reaction_role",
    "commands.voice_system"
]


# =========================
# READY
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})", flush=True)
    print("Bot ready", flush=True)


# =========================
# MAIN
# =========================

async def main():
    await asyncio.gather(
        run_web_server(),
        bot.start(TOKEN)
    )


if __name__ == "__main__":
    asyncio.run(main())
