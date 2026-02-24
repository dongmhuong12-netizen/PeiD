import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

PRIVATE_GUILD_ID = 1111391147030482944  # 👈 điền ID server cá nhân

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

async def load_extensions():
    await bot.load_extension("booster")      # V1
    await bot.load_extension("booster_v2")   # V2 (đổi tên nếu khác)

@bot.event
async def on_ready():
    try:
        # Sync global trước (cho V2)
        await bot.tree.sync()

        # Sau đó sync riêng guild cá nhân (cho V1)
        await bot.tree.sync(guild=discord.Object(id=PRIVATE_GUILD_ID))

        print("Đã sync command.")
    except Exception as e:
        print(f"Lỗi sync: {e}")

    print(f"Bot online: {bot.user}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
