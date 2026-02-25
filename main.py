import discord
from discord import app_commands
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True


class PBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced.")


bot = PBot()


@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")


# ===== P SYSTEM GROUP =====
p = app_commands.Group(
    name="p",
    description="Main P system"
)

bot.tree.add_command(p)


@p.command(name="ping", description="Check bot status")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("haii, pei is here!!´꒳`")


bot.run(TOKEN)
