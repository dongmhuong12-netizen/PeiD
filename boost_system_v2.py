import discord
from discord.ext import commands
from discord import app_commands
import random
from booster import BOOST_GIFS, EMBED_COLOR

PERSONAL_GUILD_ID = 1111391147030482944

class BoosterV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        # Không chạy V2 trong server cá nhân
        if after.guild.id == PERSONAL_GUILD_ID:
            return

        if before.premium_since is None and after.premium_since is not None:

            channel = after.guild.system_channel
            if not channel:
                return

            embed = discord.Embed(
                title="Woaaaa!! ⋆˚⟡˖ ࣪",
                description=f"then kiu {after.mention} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡",
                color=EMBED_COLOR
            )

            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_image(url=random.choice(BOOST_GIFS))

            await channel.send(embed=embed)

    # LỆNH TEST V2 (GLOBAL)
    @app_commands.command(name="testboost", description="Test hệ thống Boost V2")
    async def testboost_v2(self, interaction: discord.Interaction):
        await interaction.response.send_message("Boost V2 hoạt động 🌍", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BoosterV2(bot))
