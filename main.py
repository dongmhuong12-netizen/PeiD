import discord
import os
from discord.ext import commands


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load create trước
        await self.load_extension("commands.embed.create")

        # Sau đó load root
        await self.load_extension("core.root")

        # Clear old global commands
        self.tree.clear_commands(guild=None)

        # Sync lại
        await self.tree.sync()


bot = Bot()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
