import discord
from discord.ext import commands
from discord import app_commands
import random
from booster import DEFAULT_DESIGN  # Import default từ V1

# Giả lập cấu hình từng server (sau này có thể thay bằng DB)
guild_settings = {}

class BoostSystemV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        # Không chạy ở server cá nhân
        if after.guild.id == 1111391147030482944:
            return

        if before.premium_since is None and after.premium_since is not None:

            config = guild_settings.get(after.guild.id, {})

            title = config.get("title", DEFAULT_DESIGN["title"])
            message = config.get("message", DEFAULT_DESIGN["message"])
            color = config.get("color", DEFAULT_DESIGN["color"])
            gifs = config.get("gifs", DEFAULT_DESIGN["gifs"])

            channel = after.guild.system_channel
            if not channel:
                return

            embed = discord.Embed(
                title=title,
                description=message.format(user=after.mention),
                color=color
            )

            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_image(url=random.choice(gifs))

            await channel.send(embed=embed)

    # ===== LỆNH TEST V2 (PING SYSTEM) =====
    @app_commands.command(name="testboost", description="Test Boost V2")
    async def testboost(self, interaction: discord.Interaction):
        await interaction.response.send_message("Boost V2 hoạt động 🌍", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BoostSystemV2(bot))
