import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")

# ⚠️ ĐIỀN ID SERVER CÁ NHÂN CỦA BẠN VÀO ĐÂY
PRIVATE_GUILD_ID = 123456789012345678  # <-- đổi thành ID server của bạn

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# LOAD COGS
# =========================
async def load_extensions():
    await bot.load_extension("cogs.v1_boost")
    await bot.load_extension("cogs.v2_boost")

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    try:
        # ✅ Sync GLOBAL (V2 sẽ hiện mọi server)
        await bot.tree.sync()

        # ✅ Sync riêng cho server cá nhân (V1)
        await bot.tree.sync(guild=discord.Object(id=PRIVATE_GUILD_ID))

        print("Đã sync command.")
    except Exception as e:
        print(f"Lỗi sync: {e}")

    print(f"Bot online: {bot.user}")

# =========================
# START BOT
# =========================
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
