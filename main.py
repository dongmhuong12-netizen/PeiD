import discord
from discord.ext import commands
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")


# =========================
# KEEP ALIVE FOR RENDER WEB SERVICE
# =========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Web server running on port {port}")
    server.serve_forever()


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
    "commands.booster.lv_create",
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
    await bot.tree.sync()

    print(f"Logged in as {bot.user} ({bot.user.id})")
    print("Slash synced")
    print("Bot ready")


# =========================
# MAIN
# =========================

async def main():
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
