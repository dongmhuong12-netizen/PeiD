import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime


class WarnSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Cảnh cáo một thành viên")
    @app_commands.describe(
        member="Thành viên cần cảnh cáo",
        reason="Lý do cảnh cáo (có thể bỏ trống)"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = None
    ):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "Bạn không có quyền sử dụng lệnh này.",
                ephemeral=True
            )
            return

        if reason is None:
            reason = "Không công khai lí do phạt"

        embed = discord.Embed(
            color=0x2B2D31,
            timestamp=datetime.utcnow()
        )

        embed.set_author(
            name="CẢNH CÁO",
            icon_url="https://cdn-icons-png.flaticon.com/512/595/595067.png"
        )

        embed.description = (
            f"{member.mention} đã bị cảnh cáo.\n"
            f"> **Moderator:** {interaction.user.mention}\n"
            f"> **Lý do:** {reason}"
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(
            text=f"{interaction.guild.name}"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WarnSystem(bot))
