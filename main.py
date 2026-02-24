import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

GUILD_ID = 1111391147030482944

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

async def load_extensions():
    await bot.load_extension("booster")
    await bot.load_extension("boost_system_v2")

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")

    # Sync global (V2)
    await bot.tree.sync()

    # Sync riêng guild (V1)
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)

    print("Slash commands synced.")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
