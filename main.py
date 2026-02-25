import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")  # Railway dùng biến môi trường

GUILD_ID = 1111391147030482944  # 🔥 ĐỔI THÀNH ID SERVER CỦA BẠN

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load V1 (không chỉnh sửa)
        await self.load_extension("edit_v1")

        # Load V2 (phase mới)
        await self.load_extension("edit_v2")

        guild = discord.Object(id=GUILD_ID)

        # Copy toàn bộ global command vào guild
        self.tree.copy_global_to(guild=guild)

        # Sync riêng guild → cập nhật ngay lập tức
        await self.tree.sync(guild=guild)

        print("✅ Slash commands synced for guild.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")
    print("Bot is ready.")

bot.run(TOKEN)
