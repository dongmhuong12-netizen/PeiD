import discord
from discord.ext import commands
from discord import app_commands
import random

TOKEN = "BOT_TOKEN_CUA_CAU"

# ====== DEFAULT V1 ======
DEFAULT_GUILD_ID = 1111391147030482944
DEFAULT_CHANNEL_ID = 1139982707288440882
DEFAULT_ROLE_ID = 1111607606964932709
DEFAULT_COLOR = 0xf48fb1

DEFAULT_MESSAGE = "then kiu {user} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡"

DEFAULT_GIFS = [
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
]

# Lưu config từng server
guild_config = {}

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================

def get_config(guild_id):
    config = guild_config.get(guild_id, {})

    role_id = config.get("role", DEFAULT_ROLE_ID)
    channel_id = config.get("channel", DEFAULT_CHANNEL_ID)
    message = config.get("message", DEFAULT_MESSAGE)
    gifs = config.get("gifs", DEFAULT_GIFS)

    return role_id, channel_id, message, gifs

async def send_boost_banner(member: discord.Member):
    role_id, channel_id, message, gifs = get_config(member.guild.id)

    role = member.guild.get_role(role_id)
    channel = member.guild.get_channel(channel_id)

    if not channel:
        return

    embed = discord.Embed(
        title="Woaaaa!! ⋆˚⟡˖ ࣪",
        description=message.format(user=member.mention),
        color=DEFAULT_COLOR
    )

    embed.set_image(url=random.choice(gifs))

    await channel.send(embed=embed)

    if role:
        try:
            await member.add_roles(role)
        except:
            pass

# ========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot đã online: {bot.user}")

# ========================
# BOOST EVENT

@bot.event
async def on_member_update(before, after):
    if not before.premium_since and after.premium_since:
        await send_boost_banner(after)

    if before.premium_since and not after.premium_since:
        role_id, _, _, _ = get_config(after.guild.id)
        role = after.guild.get_role(role_id)
        if role:
            try:
                await after.remove_roles(role)
            except:
                pass

# ========================
# SLASH COMMANDS

@bot.tree.command(name="testboost", description="Test banner boost")
async def testboost(interaction: discord.Interaction):
    await interaction.response.send_message("Đã gửi banner test!", ephemeral=True)
    await send_boost_banner(interaction.user)


@bot.tree.command(name="setchannel", description="Set kênh gửi banner")
@app_commands.describe(channel="Chọn kênh")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_config.setdefault(interaction.guild.id, {})
    guild_config[interaction.guild.id]["channel"] = channel.id
    await interaction.response.send_message("Đã set channel thành công!", ephemeral=True)


@bot.tree.command(name="setrole", description="Set role boost")
@app_commands.describe(role="Chọn role")
async def setrole(interaction: discord.Interaction, role: discord.Role):
    guild_config.setdefault(interaction.guild.id, {})
    guild_config[interaction.guild.id]["role"] = role.id
    await interaction.response.send_message("Đã set role thành công!", ephemeral=True)


@bot.tree.command(name="setmessage", description="Set nội dung banner")
@app_commands.describe(message="Nhập nội dung, dùng {user}")
async def setmessage(interaction: discord.Interaction, message: str):
    guild_config.setdefault(interaction.guild.id, {})
    guild_config[interaction.guild.id]["message"] = message
    await interaction.response.send_message("Đã set message thành công!", ephemeral=True)


@bot.tree.command(name="imagelink", description="Thêm gif link")
@app_commands.describe(link="Dán link gif")
async def imagelink(interaction: discord.Interaction, link: str):
    guild_config.setdefault(interaction.guild.id, {})
    guild_config[interaction.guild.id].setdefault("gifs", DEFAULT_GIFS.copy())
    guild_config[interaction.guild.id]["gifs"].append(link)
    await interaction.response.send_message("Đã thêm gif!", ephemeral=True)

# ========================

bot.run(TOKEN)
