import discord
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load extensions
        await self.load_extension("commands.embed_commands")

        # Sync slash commands
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")


def create_bot():
    return MyBot()
