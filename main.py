import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")


# =========================
# INTENTS
# =========================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True


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
    "systems.warn_system",
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

    print(f"Logged in as {bot.user} ({bot.user.id})")
    print("Bot ready")


# =========================
# MAIN
# =========================

async def main():

    async with bot:

        await load_extensions()

        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
