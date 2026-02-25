import discord
from discord.ext import commands
import asyncio
import os

# ==========================
# 🔑 TOKEN (Railway dùng biến môi trường)
# ==========================

TOKEN = os.getenv("TOKEN")

# ==========================
# 🚀 INTENTS
# ==========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# ==========================
# 🤖 BOT CLASS
# ==========================

class PeiBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        print("🔄 Loading extensions...")

        # ===== Version 1 =====
        await self.load_extension("edit_v1")

        # ===== Version 2 =====
        await self.load_extension("edit_v2")

        print("✅ Extensions loaded.")

        # ==========================
        # 🌍 GLOBAL SYNC (QUỐC TẾ)
        # ==========================
        await self.tree.sync()
        print("🌍 Global slash commands synced.")

    async def on_ready(self):
        print("===================================")
        print(f"🔥 Logged in as {self.user}")
        print(f"🆔 Bot ID: {self.user.id}")
        print(f"📡 Connected to {len(self.guilds)} guild(s)")
        print("===================================")


# ==========================
# 🟢 START BOT
# ==========================

bot = PeiBot()

async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
