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

    print(f"Web server running on port {port}")


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
    "core.booster",
    "systems.reaction_role",
]


async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Failed to load {ext}: {e}")


# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Slash sync failed: {e}")

    print(f"Logged in as {bot.user} ({bot.user.id})")
    print("Slash synced")
    print("Bot ready")


# =========================
# MAIN
# =========================

async def main():
    await start_web_server()

    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
