import discord
from discord.ext import commands


def create_bot():

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents
    )

    @bot.event
    async def on_ready():
        print(f"✅ Logged in as {bot.user}")

        # Sync slash commands
        await bot.tree.sync()
        print("✅ Slash commands synced")

    async def load_extensions():
        await bot.load_extension("commands.embed_commands")

    bot.loop.create_task(load_extensions())

    return bot
