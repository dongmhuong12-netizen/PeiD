import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

from .permissions import is_mod_or_admin
from .utils import success_embed, error_embed, info_embed
from .logging import LogSystem


class EditV2(commands.Cog):

    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db
        self.logger = LogSystem(bot, db)

    p = app_commands.Group(name="p", description="PeiD V2 System")

    # =========================
    # ERROR HANDLER
    # =========================

    async def cog_app_command_error(self, interaction, error):
        await interaction.response.send_message(
            embed=error_embed(str(error)),
            ephemeral=True
        )

    # =========================
    # WARN
    # =========================

    @p.command(name="warn")
    @is_mod_or_admin()
    @app_commands.checks.cooldown(1, 5)
    async def warn(self, interaction: discord.Interaction,
                   member: discord.Member,
                   reason: str):

        await self.db.execute("""
        INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
        """, (interaction.guild.id, member.id,
              interaction.user.id, reason))

        await self.increment_stats(interaction.guild.id,
                                   interaction.user.id,
                                   "WARN")

        count = await self.db.fetchall("""
        SELECT id FROM warnings
        WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild.id, member.id))

        config = await self.db.fetchone("""
        SELECT auto_warn_limit FROM guild_config
        WHERE guild_id = ?
        """, (interaction.guild.id,))

        limit = config[0] if config else 3

        if len(count) >= limit:
            await member.ban(reason="Auto-ban do quá số warn")
            await self.logger.log_action(
                interaction.guild,
                "AUTO BAN",
                member.id,
                interaction.user.id
            )

        await interaction.response.send_message(
            embed=success_embed(
                f"Đã warn {member.mention} ({len(count)}/{limit})"
            )
        )

    # =========================
    # STATS
    # =========================

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

    # =========================
    # INTERNAL
    # =========================

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
