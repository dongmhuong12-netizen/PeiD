import discord
from discord import app_commands
from discord.ext import commands
import time
from .database import Database
from .permissions import PermissionManager
from .utils import success_embed, error_embed, info_embed

class EditV2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.start_time = time.time()

    async def cog_load(self):
        await self.db.connect()

    # =========================
    # ROOT GROUP
    # =========================
    p = app_commands.Group(name="p", description="Edit V2 System")

    # =========================
    # SYSTEM COMMANDS
    # =========================

    @p.command(name="stats", description="Show bot statistics")
    async def stats(self, interaction: discord.Interaction):
        uptime = int(time.time() - self.start_time)
        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Guilds", value=len(self.bot.guilds))
        embed.add_field(name="Users", value=len(self.bot.users))
        embed.add_field(name="Uptime (seconds)", value=uptime)
        await interaction.response.send_message(embed=embed)

    @p.command(name="status", description="Bot status check")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=success_embed("Bot is running perfectly."))

    # =========================
    # MODERATION
    # =========================

    @p.command(name="ban", description="Ban a user")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not await PermissionManager.is_mod(interaction):
            return await interaction.response.send_message(embed=error_embed("No permission."), ephemeral=True)

        await user.ban(reason=reason)
        await self.db.execute(
            "INSERT INTO cases (guild_id,user_id,action,moderator_id,reason) VALUES (?,?,?,?,?)",
            interaction.guild.id, user.id, "ban", interaction.user.id, reason
        )

        await interaction.response.send_message(embed=success_embed(f"Banned {user}"))

    @p.command(name="kick", description="Kick a user")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not await PermissionManager.is_mod(interaction):
            return await interaction.response.send_message(embed=error_embed("No permission."), ephemeral=True)

        await user.kick(reason=reason)

        await self.db.execute(
            "INSERT INTO cases (guild_id,user_id,action,moderator_id,reason) VALUES (?,?,?,?,?)",
            interaction.guild.id, user.id, "kick", interaction.user.id, reason
        )

        await interaction.response.send_message(embed=success_embed(f"Kicked {user}"))

    @p.command(name="warn", description="Warn a user")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not await PermissionManager.is_mod(interaction):
            return await interaction.response.send_message(embed=error_embed("No permission."), ephemeral=True)

        await self.db.execute(
            "INSERT INTO warns (guild_id,user_id,moderator_id,reason) VALUES (?,?,?,?)",
            interaction.guild.id, user.id, interaction.user.id, reason
        )

        await interaction.response.send_message(embed=success_embed(f"Warned {user}"))

    @p.command(name="history", description="View user case history")
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        rows = await self.db.fetch(
            "SELECT action,reason,timestamp FROM cases WHERE guild_id=? AND user_id=?",
            interaction.guild.id, user.id
        )

        if not rows:
            return await interaction.response.send_message(embed=info_embed("No history found."))

        embed = discord.Embed(title=f"Case History - {user}", color=discord.Color.orange())
        for action, reason, timestamp in rows:
            embed.add_field(name=f"{action.upper()} | {timestamp}", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(EditV2(bot))
