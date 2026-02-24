import discord
from discord import app_commands
import random
import os

TOKEN = os.getenv("TOKEN")

GUILD_ID = 1111391147030482944
BOOST_CHANNEL_ID = 123456789012345678  # 🔥 THAY BẰNG ID KÊNH BOOST CỦA CẬU

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập với tên {bot.user}")

@bot.tree.command(name="ping", description="Kiểm tra bot hoạt động", guild=discord.Object(id=GUILD_ID))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="testboost", description="Test thông báo boost", guild=discord.Object(id=GUILD_ID))
async def testboost(interaction: discord.Interaction):

    channel = bot.get_channel(BOOST_CHANNEL_ID)

    gifs = [
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
        "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif"
    ]

    random_gif = random.choice(gifs)

    embed = discord.Embed(
        title="Woaaaa!! ⋆˚⟡˖ ࣪",
        description=f"then kiu {interaction.user.mention} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡",
        color=discord.Color.purple()
    )

    embed.set_image(url=random_gif)

    await channel.send(embed=embed)
    await interaction.response.send_message("Đã gửi thông báo boost test.", ephemeral=True)

bot.run(TOKEN)
