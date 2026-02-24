import discord
from discord.ext import commands
from discord import app_commands
import random

GUILD_ID = 1111391147030482944
BOOST_CHANNEL_ID = 1139982707288440882
BOOSTER_ROLE_ID = 1111607606964932709
EMBED_COLOR = 0xf48fb1

BOOST_GIFS = [
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
]

class BoosterV1(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # BOOST EVENT V1
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        if after.guild.id != GUILD_ID:
            return

        if before.premium_since is None and after.premium_since is not None:

            role = after.guild.get_role(BOOSTER_ROLE_ID)
            channel = after.guild.get_channel(BOOST_CHANNEL_ID)

            if role:
                await after.add_roles(role)

            if channel:
                embed = discord.Embed(
                    title="Woaaaa!! ⋆˚⟡˖ ࣪",
                    description=f"then kiu {after.mention} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡",
                    color=EMBED_COLOR
                )

                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_image(url=random.choice(BOOST_GIFS))

                await channel.send(embed=embed)

    # LỆNH TEST V1
    @app_commands.command(name="1testboost", description="Test hệ thống Boost V1")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def testboost_v1(self, interaction: discord.Interaction):
        await interaction.response.send_message("Boost V1 hoạt động 💎", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BoosterV1(bot))
