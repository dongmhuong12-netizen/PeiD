import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


bot.run(TOKEN)
