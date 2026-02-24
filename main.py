import discord
from discord import app_commands
import os

TOKEN = os.getenv("TOKEN")

BOOST_CHANNEL_ID = 1139982707288440882  # ID kênh boost
SERVER_ID = 1111391147030482944        # ID server

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    # Xoá toàn bộ command global cũ (nếu có)
    tree.clear_commands(guild=None)
    await tree.sync()

    # Sync command theo server (hiện ngay, không delay)
    await tree.sync(guild=discord.Object(id=SERVER_ID))

    print(f"Logged in as {client.user}")


# ===== LỆNH /ping =====
@tree.command(
    name="ping",
    description="Kiểm tra bot còn sống không",
    guild=discord.Object(id=SERVER_ID)
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong 🏓")


# ===== LỆNH /testboost =====
@tree.command(
    name="testboost",
    description="Test thông báo boost",
    guild=discord.Object(id=SERVER_ID)
)
async def testboost(interaction: discord.Interaction):
    channel = client.get_channel(BOOST_CHANNEL_ID)

    embed = discord.Embed(
        title="💎 Server Boost!",
        description=f"Cảm ơn {interaction.user.mention} đã boost server!",
        color=discord.Color.purple()
    )

    embed.set_image(url="https://media.giphy.com/media/26u4cqiYI30juCOGY/giphy.gif")

    if channel:
        await channel.send(embed=embed)
        await interaction.response.send_message("Đã gửi thông báo boost!", ephemeral=True)
    else:
        await interaction.response.send_message("Không tìm thấy kênh boost!", ephemeral=True)


client.run(TOKEN)
