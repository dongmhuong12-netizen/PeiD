import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load P System
        await self.load_extension("p_system")

        # Sync global slash commands
        await self.tree.sync()
        print("✅ Slash commands synced globally.")


bot = Bot()


@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")
    print("🌙 P System is running.")


bot.run(TOKEN)
