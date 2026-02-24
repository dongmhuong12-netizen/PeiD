import discord
from discord import app_commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # để có thể tag và xử lý member

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

# Slash command /ping
@tree.command(name="ping", description="Kiểm tra bot còn sống không")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

client.run(os.getenv("TOKEN"))
