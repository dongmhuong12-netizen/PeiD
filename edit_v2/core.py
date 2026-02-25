import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

from .permissions import is_mod_or_admin
from .utils import success_embed, error_embed, info_embed
from .logging import LogSystem
from .views import ConfirmView


class EditV2(commands.Cog):

    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db
        self.logger = LogSystem(bot, db)

    p = app_commands.Group(name="p", description="PeiD V2 System")

    # ===============================
    # ERROR HANDLER
    # ===============================

    async def cog_app_command_error(self, interaction, error):
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=error_embed(str(error)),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=error_embed(str(error)),
                ephemeral=True
            )

    # ===============================
    # SETUP
    # ===============================

    @p.command(name="setup")
    @app_commands.checks.has_permissions(administrator=True)
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

        log_channel = await guild.create_text_channel("v2-logs")
        mod_role = await guild.create_role(name="V2 Moderator")

        await self.db.execute("""
        INSERT OR REPLACE INTO guild_config
        (guild_id, log_channel_id, mod_role_id, auto_warn_limit, setup_completed)
        VALUES (?, ?, ?, 3, 1)
        """, (guild.id, log_channel.id, mod_role.id))

        await interaction.response.send_message(
            embed=success_embed("Setup V2 hoàn tất."),
            ephemeral=True
        )

    # ===============================
    # INFO
    # ===============================

    @p.command(name="info")
    async def info(self, interaction: discord.Interaction):

        embed = info_embed(
            "PeiD V2 System",
            "Commands:\n"
            "/p setup\n"
            "/p kick\n"
            "/p ban\n"
            "/p warn\n"
            "/p warnings\n"
            "/p clearwarn\n"
            "/p mute\n"
            "/p unmute\n"
            "/p stats"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ===============================
    # KICK
    # ===============================

    @p.command(name="kick")
    @is_mod_or_admin()
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
        await self.increment_stats(interaction.guild.id,
                                   interaction.user.id,
                                   "KICK")

        await self.logger.log_action(
            interaction.guild,
            "KICK",
            member.id,
            interaction.user.id
        )

        await interaction.followup.send(
            embed=success_embed(f"Đã kick {member.mention}")
        )

    # ===============================
    # BAN
    # ===============================

    @p.command(name="ban")
    @is_mod_or_admin()
    async def ban(self, interaction: discord.Interaction,
                  member: discord.Member,
                  reason: str = "No reason"):

        await member.ban(reason=reason)

        await self.increment_stats(interaction.guild.id,
                                   interaction.user.id,
                                   "BAN")

        await self.logger.log_action(
            interaction.guild,
            "BAN",
            member.id,
            interaction.user.id
        )

        await interaction.response.send_message(
            embed=success_embed(f"Đã ban {member.mention}")
        )

    # ===============================
    # WARN
    # ===============================

    @p.command(name="warn")
    @is_mod_or_admin()
    @app_commands.checks.cooldown(1, 5)
    async def warn(self, interaction: discord.Interaction,
                   member: discord.Member,
                   reason: str):

        await self.db.execute("""
        INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
        """, (interaction.guild.id,
              member.id,
              interaction.user.id,
              reason))

        await self.increment_stats(interaction.guild.id,
                                   interaction.user.id,
                                   "WARN")

        rows = await self.db.fetchall("""
        SELECT id FROM warnings
        WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild.id, member.id))

        config = await self.db.fetchone("""
        SELECT auto_warn_limit FROM guild_config
        WHERE guild_id = ?
        """, (interaction.guild.id,))

        limit = config[0] if config else 3

        if len(rows) >= limit:
            await member.ban(reason="Auto-ban do quá số warn")
            await self.logger.log_action(
                interaction.guild,
                "AUTO BAN",
                member.id,
                interaction.user.id
            )

        await interaction.response.send_message(
            embed=success_embed(
                f"Đã warn {member.mention} ({len(rows)}/{limit})"
            )
        )

    # ===============================
    # WARNINGS
    # ===============================

    @p.command(name="warnings")
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

    # ===============================
    # CLEAR WARN
    # ===============================

    @p.command(name="clearwarn")
    @is_mod_or_admin()
    async def clearwarn(self, interaction: discord.Interaction,
                        member: discord.Member):

        await self.db.execute("""
        DELETE FROM warnings
        WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild.id, member.id))

        await interaction.response.send_message(
            embed=success_embed(f"Đã xóa warn của {member.mention}")
        )

    # ===============================
    # MUTE
    # ===============================

    @p.command(name="mute")
    @is_mod_or_admin()
    async def mute(self, interaction: discord.Interaction,
                   member: discord.Member,
                   minutes: int):

        duration = timedelta(minutes=minutes)
        await member.timeout(duration)

        await self.increment_stats(interaction.guild.id,
                                   interaction.user.id,
                                   "MUTE")

        await interaction.response.send_message(
            embed=success_embed(f"Đã mute {member.mention} {minutes} phút")
        )

    # ===============================
    # UNMUTE
    # ===============================

    @p.command(name="unmute")
    @is_mod_or_admin()
    async def unmute(self, interaction: discord.Interaction,
                     member: discord.Member):

        await member.timeout(None)

        await interaction.response.send_message(
            embed=success_embed(f"Đã unmute {member.mention}")
        )

    # ===============================
    # STATS
    # ===============================

    @p.command(name="stats")
    async def stats(self, interaction: discord.Interaction):

        rows = await self.db.fetchall("""
        SELECT moderator_id, action, count
        FROM stats WHERE guild_id = ?
        """, (interaction.guild.id,))

        if not rows:
            await interaction.response.send_message(
                embed=info_embed("Stats", "Chưa có dữ liệu."),
                ephemeral=True
            )
            return

        desc = ""
        for r in rows:
            desc += f"<@{r[0]}> - {r[1]}: {r[2]}\n"

        await interaction.response.send_message(
            embed=info_embed("Moderation Stats", desc)
        )

    # ===============================
    # INTERNAL STATS
    # ===============================

    async def increment_stats(self, guild_id, mod_id, action):

        existing = await self.db.fetchone("""
        SELECT count FROM stats
        WHERE guild_id = ? AND moderator_id = ? AND action = ?
        """, (guild_id, mod_id, action))

        if existing:
            await self.db.execute("""
            UPDATE stats
            SET count = count + 1
            WHERE guild_id = ? AND moderator_id = ? AND action = ?
            """, (guild_id, mod_id, action))
        else:
            await self.db.execute("""
            INSERT INTO stats (guild_id, moderator_id, action, count)
            VALUES (?, ?, ?, 1)
            """, (guild_id, mod_id, action))
