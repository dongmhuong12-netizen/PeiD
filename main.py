import discord
from discord import app_commands
import os

TOKEN = os.getenv("TOKEN")

BOOST_CHANNEL_ID = 1139982707288440882  # ID kênh boost của cậu
SERVER_ID = 1111391147030482944  # ID server của cậu

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=SERVER_ID))
    print(f"Logged in as {client.user}")

# Lệnh /ping
@tree.command(
    name="ping",
    description="Kiểm tra bot còn sống không",
    guild=discord.Object(id=SERVER_ID)
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Lệnh /testboost để test thủ công
@tree.command(
    name="testboost",
    description="Test thông báo boost",
    guild=discord.Object(id=SERVER_ID)
)
async def testboost(interaction: discord.Interaction):
    channel = client.get_channel(BOOST_CHANNEL_ID)

    embed = discord.Embed(
        title="💎 Server Boost!",
        description=f"Cảm ơn {interaction.user.mention} đã boost server ✨",
        color=discord.Color.purple()
    )

    embed.set_image(url="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif")

    await channel.send(content=interaction.user.mention, embed=embed)
    await interaction.response.send_message("Đã gửi thông báo boost!", ephemeral=True)

# Tự động khi có người boost thật
@client.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        channel = client.get_channel(BOOST_CHANNEL_ID)

        embed = discord.Embed(
            title="💎 Server Boost!",
            description=f"Cảm ơn {after.mention} đã boost server ✨",
            color=discord.Color.purple()
        )

        embed.set_image(url="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif")

        await channel.send(content=after.mention, embed=embed)

client.run(TOKEN)
