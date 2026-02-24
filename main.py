import discord
from discord import app_commands
import os
import random

TOKEN = os.getenv("TOKEN")

SERVER_ID = 1111391147030482944
BOOST_CHANNEL_ID = 1139982707288440882
BOOST_ROLE_ID = 1111607606964932709

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=SERVER_ID))
    print(f"Bot đã online với tên {client.user}")


# ===== LỆNH PING =====
@tree.command(
    name="ping",
    description="Kiểm tra bot hoạt động",
    guild=discord.Object(id=SERVER_ID)
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong 💗")


# ===== LỆNH TEST BOOST =====
@tree.command(
    name="testboost",
    description="Test thông báo boost",
    guild=discord.Object(id=SERVER_ID)
)
async def testboost(interaction: discord.Interaction):

    channel = client.get_channel(BOOST_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message("Không tìm thấy kênh boost.", ephemeral=True)
        return

    await send_boost_embed(channel, interaction.user)
    await interaction.response.send_message("Đã gửi test boost 💗", ephemeral=True)


# ===== TỰ ĐỘNG PHÁT HIỆN BOOST =====
@client.event
async def on_member_update(before: discord.Member, after: discord.Member):

    guild = after.guild
    role = guild.get_role(BOOST_ROLE_ID)

    # Người vừa bắt đầu boost
    if before.premium_since is None and after.premium_since is not None:

        channel = client.get_channel(BOOST_CHANNEL_ID)
        if channel:
            await send_boost_embed(channel, after)

        if role and role not in after.roles:
            await after.add_roles(role)

    # Người ngừng boost
    if before.premium_since is not None and after.premium_since is None:

        if role and role in after.roles:
            await after.remove_roles(role)


# ===== HÀM GỬI EMBED =====
async def send_boost_embed(channel, user):

    gif_list = [
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif"
    ]

    chosen_gif = random.choice(gif_list)

    embed = discord.Embed(
        title="Woaaaa!! ⋆˚⟡˖ ࣪",
        description=f"then kiu {user.mention} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡",
        color=discord.Color(0xF8BBD0)
    )

    embed.set_image(url=chosen_gif)

    await channel.send(embed=embed)


client.run(TOKEN)
