import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime


class WarnSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_hours = 24
        self.user_levels = {}

    @app_commands.command(name="warn", description="Cảnh cáo thành viên")
    @app_commands.describe(
        member="Thành viên cần cảnh cáo",
        reason="Lý do (có thể bỏ trống)"
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

        if member.bot:
            await interaction.response.send_message(
                "Không thể cảnh cáo bot.",
                ephemeral=True
            )
            return

        if reason is None:
            reason = "Không công khai lý do phạt."

        user_id = member.id
        current_level = self.user_levels.get(user_id, 0) + 1
        self.user_levels[user_id] = current_level

        embed = discord.Embed(
            color=0x2B2D31,
            timestamp=datetime.utcnow()
        )

        embed.description = (
            "━━━━━━━━━━━━━━━━━━\n"
            "**WARNING**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **CẤP ĐỘ:** LEVEL **{current_level}**\n"
            f"• **ĐỐI TƯỢNG:** {member.mention}  `{member.id}`\n"
            f"• **HÌNH PHẠT:** WARN\n\n"
            f"**LÝ DO**\n{reason}\n\n"
            f"• **RESET:** {self.reset_hours} GIỜ\n"
            f"• **NẾU TÁI PHẠM KHI CHƯA HẾT RESET:** LEVEL {current_level + 1}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "**HỆ THỐNG QUẢN LÝ KỶ LUẬT**"
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WarnSystem(bot))
