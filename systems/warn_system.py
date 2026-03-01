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
                "❌ Bạn không có quyền sử dụng lệnh này.",
                ephemeral=True
            )
            return

        if reason is None:
            reason = "Không công khai lí do phạt"

        embed = discord.Embed(
            title="⚠️ | CẢNH CÁO THÀNH VIÊN",
            description=f"{member.mention} đã bị cảnh cáo.",
            color=0xFF9F1C,
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="👤 Thành viên",
            value=f"{member.mention}\nID: `{member.id}`",
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=f"{interaction.user.mention}",
            inline=False
        )

        embed.add_field(
            name="📄 Lý do",
            value=f"```{reason}```",
            inline=False
        )

        embed.set_footer(text=f"Server: {interaction.guild.name}")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WarnSystem(bot))
