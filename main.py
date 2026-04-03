import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")


# =========================
# WEB SERVER FOR RENDER
# =========================

async def health(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Web server running on port {port}", flush=True)


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
# EXTENSIONS
# =========================

EXTENSIONS = [
    "core.root",
    "systems.reaction_role",
]


async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}", flush=True)
        except Exception as e:
            print(f"Failed to load {ext}: {e}", flush=True)


# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Slash synced: {len(synced)}", flush=True)
    except Exception as e:
        print(f"Slash sync failed: {e}", flush=True)

    print(f"Logged in as {bot.user} ({bot.user.id})", flush=True)
    print("Bot ready", flush=True)


# =========================
# BOT RUNNER
# =========================

async def run_bot():
    async with bot:
        await load_extensions()
        print("Starting bot login...", flush=True)
        await bot.start(TOKEN)


# =========================
# MAIN
# =========================

async def main():
    await start_web_server()
    await run_bot()


if __name__ == "__main__":
    asyncio.run(main())
