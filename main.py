import discord
from discord import app_commands
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced.")

bot = Bot()


@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")


# ====== P SYSTEM ROOT ======
p = app_commands.Group(name="p", description="Main P system commands")
bot.tree.add_command(p)


@p.command(name="ping", description="Test P system")
async def p_ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 P system is alive.")


bot.run(TOKEN)
