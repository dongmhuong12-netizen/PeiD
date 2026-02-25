import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import datetime
import asyncio

# ===============================
# EDIT V2 - ULTIMATE PUBLIC CORE
# ===============================

class EditV2(commands.Cog):

    # ===============================
    # INIT
    # ===============================

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("pei_v2.db")
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.setup_database()

    # ===============================
    # DATABASE
    # ===============================

    def setup_database(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            greet_channel INTEGER,
            greet_message TEXT,
            leave_channel INTEGER,
            leave_message TEXT,
            log_channel INTEGER
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            data TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS autoroles (
            guild_id INTEGER,
            role_id INTEGER
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            timestamp TEXT
        )
        """)

        self.db.commit()

    def ensure_guild(self, guild_id: int):
        self.cursor.execute("SELECT guild_id FROM guilds WHERE guild_id = ?", (guild_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO guilds (guild_id) VALUES (?)", (guild_id,))
            self.db.commit()

    # ===============================
    # ROOT GROUP
    # ===============================

    p = app_commands.Group(name="p", description="Pei Ultimate Public System")

    # =========================================================
    # EMBED SYSTEM
    # =========================================================

    embed = app_commands.Group(name="embed", description="Embed system", parent=p)

    @embed.command(name="create", description="Create saved embed")
    async def embed_create(self, interaction: discord.Interaction, name: str, title: str, description: str):
        self.ensure_guild(interaction.guild.id)

        embed_data = {
            "title": title,
            "description": description,
            "color": discord.Color.blurple().value
        }

        self.cursor.execute(
            "INSERT INTO embeds (guild_id, name, data) VALUES (?, ?, ?)",
            (interaction.guild.id, name, json.dumps(embed_data))
        )
        self.db.commit()

        await interaction.response.send_message("✅ Embed saved.", ephemeral=True)

    @embed.command(name="send", description="Send saved embed")
    async def embed_send(self, interaction: discord.Interaction, name: str, channel: discord.TextChannel):
        self.cursor.execute(
            "SELECT data FROM embeds WHERE guild_id = ? AND name = ?",
            (interaction.guild.id, name)
        )
        row = self.cursor.fetchone()
        if not row:
            await interaction.response.send_message("❌ Embed not found.", ephemeral=True)
            return

        data = json.loads(row["data"])
        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=data["color"]
        )

        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Sent.", ephemeral=True)

    @embed.command(name="delete", description="Delete saved embed")
    async def embed_delete(self, interaction: discord.Interaction, name: str):
        self.cursor.execute(
            "DELETE FROM embeds WHERE guild_id = ? AND name = ?",
            (interaction.guild.id, name)
        )
        self.db.commit()
        await interaction.response.send_message("🗑 Deleted.", ephemeral=True)

    @embed.command(name="list", description="List saved embeds")
    async def embed_list(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT name FROM embeds WHERE guild_id = ?", (interaction.guild.id,))
        rows = self.cursor.fetchall()

        if not rows:
            await interaction.response.send_message("No embeds.", ephemeral=True)
            return

        names = "\n".join([r["name"] for r in rows])
        await interaction.response.send_message(f"📦 Embeds:\n{names}", ephemeral=True)

    # =========================================================
    # GREET SYSTEM
    # =========================================================

    greet = app_commands.Group(name="greet", description="Greet system", parent=p)

    @greet.command(name="setup", description="Setup greet")
    async def greet_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        self.ensure_guild(interaction.guild.id)
        self.cursor.execute(
            "UPDATE guilds SET greet_channel = ?, greet_message = ? WHERE guild_id = ?",
            (channel.id, message, interaction.guild.id)
        )
        self.db.commit()
        await interaction.response.send_message("✅ Greet configured.", ephemeral=True)

    @greet.command(name="leave", description="Setup leave")
    async def greet_leave(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        self.ensure_guild(interaction.guild.id)
        self.cursor.execute(
            "UPDATE guilds SET leave_channel = ?, leave_message = ? WHERE guild_id = ?",
            (channel.id, message, interaction.guild.id)
        )
        self.db.commit()
        await interaction.response.send_message("✅ Leave configured.", ephemeral=True)

    # =========================================================
    # AUTOROLE
    # =========================================================

    autorole = app_commands.Group(name="autorole", description="Autorole system", parent=p)

    @autorole.command(name="add", description="Add autorole")
    async def autorole_add(self, interaction: discord.Interaction, role: discord.Role):
        self.cursor.execute(
            "INSERT INTO autoroles (guild_id, role_id) VALUES (?, ?)",
            (interaction.guild.id, role.id)
        )
        self.db.commit()
        await interaction.response.send_message("✅ Role added.", ephemeral=True)

    @autorole.command(name="remove", description="Remove autorole")
    async def autorole_remove(self, interaction: discord.Interaction, role: discord.Role):
        self.cursor.execute(
            "DELETE FROM autoroles WHERE guild_id = ? AND role_id = ?",
            (interaction.guild.id, role.id)
        )
        self.db.commit()
        await interaction.response.send_message("🗑 Role removed.", ephemeral=True)

    @autorole.command(name="list", description="List autoroles")
    async def autorole_list(self, interaction: discord.Interaction):
        self.cursor.execute(
            "SELECT role_id FROM autoroles WHERE guild_id = ?",
            (interaction.guild.id,)
        )
        rows = self.cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No autoroles.", ephemeral=True)
            return
        roles = "\n".join([f"<@&{r['role_id']}>" for r in rows])
        await interaction.response.send_message(roles, ephemeral=True)

    # =========================================================
    # MODERATION
    # =========================================================

    moderation = app_commands.Group(name="moderation", description="Moderation system", parent=p)

    @moderation.command(name="ban")
    async def mod_ban(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await user.ban(reason=reason)
        await interaction.response.send_message("🔨 User banned.")

    @moderation.command(name="kick")
    async def mod_kick(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await user.kick(reason=reason)
        await interaction.response.send_message("👢 User kicked.")

    @moderation.command(name="warn")
    async def mod_warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        self.cursor.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                interaction.guild.id,
                user.id,
                interaction.user.id,
                reason,
                datetime.datetime.utcnow().isoformat()
            )
        )
        self.db.commit()
        await interaction.response.send_message("⚠ Warning issued.")

    @moderation.command(name="history")
    async def mod_history(self, interaction: discord.Interaction, user: discord.Member):
        self.cursor.execute(
            "SELECT reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ?",
            (interaction.guild.id, user.id)
        )
        rows = self.cursor.fetchall()
        if not rows:
            await interaction.response.send_message("No warnings.", ephemeral=True)
            return
        text = "\n".join([f"{r['timestamp']} - {r['reason']}" for r in rows])
        await interaction.response.send_message(text, ephemeral=True)

    # =========================================================
    # SYSTEM
    # =========================================================

    system = app_commands.Group(name="system", description="System info", parent=p)

    @system.command(name="stats")
    async def system_stats(self, interaction: discord.Interaction):
        guilds = len(self.bot.guilds)
        users = sum(g.member_count for g in self.bot.guilds)
        await interaction.response.send_message(
            f"Servers: {guilds}\nUsers: {users}"
        )

    @system.command(name="status")
    async def system_status(self, interaction: discord.Interaction):
        await interaction.response.send_message("🟢 Bot operational.")

    # =========================================================
    # EVENTS
    # =========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self.cursor.execute("SELECT greet_channel, greet_message FROM guilds WHERE guild_id = ?", (member.guild.id,))
        row = self.cursor.fetchone()

        if row and row["greet_channel"] and row["greet_message"]:
            channel = member.guild.get_channel(row["greet_channel"])
            if channel:
                msg = row["greet_message"].replace("{member}", member.mention)
                await channel.send(msg)

        self.cursor.execute("SELECT role_id FROM autoroles WHERE guild_id = ?", (member.guild.id,))
        roles = self.cursor.fetchall()
        for r in roles:
            role = member.guild.get_role(r["role_id"])
            if role:
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        self.cursor.execute("SELECT leave_channel, leave_message FROM guilds WHERE guild_id = ?", (member.guild.id,))
        row = self.cursor.fetchone()

        if row and row["leave_channel"] and row["leave_message"]:
            channel = member.guild.get_channel(row["leave_channel"])
            if channel:
                msg = row["leave_message"].replace("{member}", member.name)
                await channel.send(msg)

    # =========================================================
    # ERROR HANDLER
    # =========================================================

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EditV2(bot))
