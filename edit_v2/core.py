import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import asyncio

from .permissions import is_admin, is_owner
from .utils import success_embed, error_embed, info_embed
from .logging import LogSystem
from .views import ConfirmView


class EditV2(commands.Cog):

    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db
        self.logger = LogSystem(bot, db)

    # ==============================
    # Slash Group /p
    # ==============================

    p = app_commands.Group(name="p", description="PeiD V2 System")

    # ==============================
    # SETUP
    # ==============================

    @p.command(name="setup", description="Thiết lập hệ thống V2")
    @is_admin()
    async def setup_system(self, interaction: discord.Interaction):

        guild = interaction.guild

        existing = await self.db.fetchone(
            "SELECT setup_completed FROM guild_config WHERE guild_id = ?",
            (guild.id,)
        )

        if existing and existing[0] == 1:
            await interaction.response.send_message(
                embed=error_embed("Server đã setup trước đó."),
                ephemeral=True
            )
            return

        # Create log channel
        log_channel = await guild.create_text_channel("v2-logs")

        # Create mod role
        mod_role = await guild.create_role(name="V2 Moderator")

        await self.db.execute("""
        INSERT OR REPLACE INTO guild_config
        (guild_id, log_channel_id, mod_role_id, setup_completed)
        VALUES (?, ?, ?, 1)
        """, (guild.id, log_channel.id, mod_role.id))

        await interaction.response.send_message(
            embed=success_embed("Setup V2 hoàn tất."),
            ephemeral=True
        )

    # ==============================
    # INFO
    # ==============================

    @p.command(name="info", description="Thông tin hệ thống V2")
    async def info(self, interaction: discord.Interaction):

        embed = info_embed(
            "PeiD V2",
            "Hệ thống moderation nâng cấp tối đa.\n\n"
            "Commands:\n"
            "/p setup\n"
            "/p kick\n"
            "/p ban\n"
            "/p warn\n"
            "/p warnings\n"
            "/p clearwarn\n"
            "/p mute\n"
            "/p unmute"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==============================
    # KICK
    # ==============================

    @p.command(name="kick", description="Kick thành viên")
    @is_admin()
    async def kick(self, interaction: discord.Interaction,
                   member: discord.Member,
                   reason: str = "No reason"):

        view = ConfirmView()
        await interaction.response.send_message(
            embed=info_embed("Xác nhận Kick", f"Kick {member.mention}?"),
            view=view,
            ephemeral=True
        )

        await view.wait()

        if not view.value:
            return

        await member.kick(reason=reason)

        await self.logger.log_action(
            interaction.guild, "KICK",
            member.id, interaction.user.id
        )

        await interaction.followup.send(
            embed=success_embed(f"Đã kick {member.mention}")
        )

    # ==============================
    # BAN
    # ==============================

    @p.command(name="ban", description="Ban thành viên")
    @is_admin()
    async def ban(self, interaction: discord.Interaction,
                  member: discord.Member,
                  reason: str = "No reason"):

        await member.ban(reason=reason)

        await self.logger.log_action(
            interaction.guild, "BAN",
            member.id, interaction.user.id
        )

        await interaction.response.send_message(
            embed=success_embed(f"Đã ban {member.mention}")
        )

    # ==============================
    # WARN
    # ==============================

    @p.command(name="warn", description="Cảnh cáo thành viên")
    @is_admin()
    async def warn(self, interaction: discord.Interaction,
                   member: discord.Member,
                   reason: str):

        await self.db.execute("""
        INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
        """, (interaction.guild.id, member.id,
              interaction.user.id, reason))

        await self.logger.log_action(
            interaction.guild, "WARN",
            member.id, interaction.user.id
        )

        await interaction.response.send_message(
            embed=success_embed(f"Đã warn {member.mention}")
        )

    # ==============================
    # WARNINGS
    # ==============================

    @p.command(name="warnings", description="Xem danh sách warn")
    async def warnings(self, interaction: discord.Interaction,
                       member: discord.Member):

        rows = await self.db.fetchall("""
        SELECT reason, timestamp FROM warnings
        WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild.id, member.id))

        if not rows:
            await interaction.response.send_message(
                embed=info_embed("Warnings", "Không có cảnh cáo."),
                ephemeral=True
            )
            return

        desc = ""
        for r in rows:
            desc += f"- {r[0]} ({r[1]})\n"

        await interaction.response.send_message(
            embed=info_embed(f"Warnings của {member}", desc),
            ephemeral=True
        )

    # ==============================
    # CLEAR WARN
    # ==============================

    @p.command(name="clearwarn", description="Xóa toàn bộ warn")
    @is_admin()
    async def clearwarn(self, interaction: discord.Interaction,
                        member: discord.Member):

        await self.db.execute("""
        DELETE FROM warnings
        WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild.id, member.id))

        await interaction.response.send_message(
            embed=success_embed(f"Đã xóa warn của {member.mention}")
        )

    # ==============================
    # MUTE (Timeout)
    # ==============================

    @p.command(name="mute", description="Mute thành viên")
    @is_admin()
    async def mute(self, interaction: discord.Interaction,
                   member: discord.Member,
                   minutes: int):

        duration = timedelta(minutes=minutes)

        await member.timeout(duration)

        await self.logger.log_action(
            interaction.guild, "MUTE",
            member.id, interaction.user.id
        )

        await interaction.response.send_message(
            embed=success_embed(f"Đã mute {member.mention} {minutes} phút")
        )

    # ==============================
    # UNMUTE
    # ==============================

    @p.command(name="unmute", description="Bỏ mute")
    @is_admin()
    async def unmute(self, interaction: discord.Interaction,
                     member: discord.Member):

        await member.timeout(None)

        await self.logger.log_action(
            interaction.guild, "UNMUTE",
            member.id, interaction.user.id
        )

        await interaction.response.send_message(
            embed=success_embed(f"Đã unmute {member.mention}")
        )
