import discord
from discord.ext import commands

from storage.json_db import JSONDatabase


class PBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.db = JSONDatabase()

    async def setup_hook(self):
        await self.load_extension("commands.embed.embed_commands")
        await self.tree.sync()
        print("✅ Slash commands synced.")


def create_bot():
    return PBot()
