import discord
from discord.ext import commands
from discord import app_commands
import random

# ===== ID CỦA BẠN (GIỮ NGUYÊN NẾU ĐANG DÙNG) =====
BOOST_CHANNEL_ID = 1139982707288440882
BOOST_ROLE_ID = 1111607606964932709


class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =============================
    # GỬI EMBED BOOST (V1)
    # =============================
    async def send_boost_embed(self, channel, user):
        gif_list = [
            # Giữ nguyên list gif của bạn nếu có
            "https://media.tenor.com/3vR6kG9yFZkAAAAC/anime-thank-you.gif"
        ]

        chosen_gif = random.choice(gif_list)

        embed = discord.Embed(
            title="Woaaaa!! ✧˚₊‧",
            description=f"then kiu {user.mention} đã buff server ✨",
            color=discord.Color(0xF8BBD0)
        )

        embed.set_image(url=chosen_gif)
        await channel.send(embed=embed)

    # =============================
    # SLASH COMMAND V1
    # =============================
    @app_commands.command(name="1testboost", description="Test boost V1")
    async def testboost(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(BOOST_CHANNEL_ID)

        if not channel:
            await interaction.response.send_message("❌ Không tìm thấy kênh boost.")
            return

        await self.send_boost_embed(channel, interaction.user)
        await interaction.response.send_message("✅ Đã gửi thông báo boost (V1).")

    # =============================
    # AUTO DETECT BOOST
    # =============================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        role = after.guild.get_role(BOOST_ROLE_ID)

        # Khi bắt đầu boost
        if before.premium_since is None and after.premium_since is not None:
            channel = self.bot.get_channel(BOOST_CHANNEL_ID)

            if channel:
                await self.send_boost_embed(channel, after)

            if role and role not in after.roles:
                await after.add_roles(role)

        # Khi bỏ boost
        if before.premium_since is not None and after.premium_since is None:
            if role and role in after.roles:
                await after.remove_roles(role)


async def setup(bot):
    await bot.add_cog(Booster(bot))
