import discord
from discord import app_commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

BOOST_CHANNEL_ID = 1139982707288440882  # thay bằng ID kênh của cậu

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

# Slash command /ping
@tree.command(name="ping", description="Kiểm tra bot còn sống không")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Slash command /testboost để test
@tree.command(name="testboost", description="Test thông báo boost")
async def testboost(interaction: discord.Interaction):
    channel = client.get_channel(BOOST_CHANNEL_ID)

    embed = discord.Embed(
        title="💎 Server Boost!",
        description=f"Cảm ơn {interaction.user.mention} đã boost server!",
        color=discord.Color.purple()
    )

    embed.set_image(url="https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif")

    await channel.send(content=interaction.user.mention, embed=embed)
    await interaction.response.send_message("Đã gửi thông báo test boost!", ephemeral=True)

# Tự động khi có người boost thật
@client.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        channel = client.get_channel(BOOST_CHANNEL_ID)

        embed = discord.Embed(
            title="💎 Server Boost!",
            description=f"Cảm ơn {after.mention} đã boost server!",
            color=discord.Color.purple()
        )

        embed.set_image(url="https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif")

        await channel.send(content=after.mention, embed=embed)

client.run(os.getenv("TOKEN"))
