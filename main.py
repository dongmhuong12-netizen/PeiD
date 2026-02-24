import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1111391147030482944

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    await bot.load_extension("booster_v1")
    await bot.load_extension("boost_system_v2")

@bot.event
async def on_ready():
    print(f"Online: {bot.user}")

    # Sync global (V2)
    await bot.tree.sync()

    # Sync riêng guild (V1)
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    print("Slash synced.")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
