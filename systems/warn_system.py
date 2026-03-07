# =========================
# IMPORTS
# =========================

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime, timedelta


# =========================
# FILE PATH
# =========================

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


# =========================
# LOCK (ANTI DATA RACE)
# =========================

file_lock = asyncio.Lock()


# =========================
# WARN SYSTEM
# =========================

class WarnSystem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.warn_cooldown = {}

    # =========================
    # JSON LOAD
    # =========================

    async def load_json(self, file):

        async with file_lock:

            if not os.path.exists(file):
                with open(file, "w") as f:
                    json.dump({}, f)

            with open(file, "r") as f:
                return json.load(f)

    # =========================
    # JSON SAVE
    # =========================

    async def save_json(self, file, data):

        async with file_lock:

            with open(file, "w") as f:
                json.dump(data, f, indent=4)

    # =========================
    # GET GUILD DATA
    # =========================

    def get_guild_data(self, data, guild_id):

        guild_id = str(guild_id)

        if guild_id not in data:
            data[guild_id] = {}

        return data[guild_id]

    # =========================
    # GET USER DATA
    # =========================

    def get_user_data(self, guild_data, user_id):

        user_id = str(user_id)

        if user_id not in guild_data:

            guild_data[user_id] = {
                "warns": []
            }

        return guild_data[user_id]

    # =========================
    # SET LOG CHANNEL
    # =========================

    @app_commands.command(name="setlog", description="Set warn log channel")
    @app_commands.checks.has_permissions(administrator=True)

    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):

        config = await self.load_json(CONFIG_FILE)

        guild_id = str(interaction.guild.id)

        if guild_id not in config:
            config[guild_id] = {}

        config[guild_id]["log_channel"] = channel.id

        await self.save_json(CONFIG_FILE, config)

        embed = discord.Embed(
            title="Warn Log Channel Set",
            description=f"Log channel set to {channel.mention}",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    # =========================
    # SET WARN LEVEL
    # =========================

    @app_commands.command(name="setlevel", description="Set warn punish levels")
    @app_commands.checks.has_permissions(administrator=True)

    async def setlevel(self, interaction: discord.Interaction, warn: int, action: str):

        config = await self.load_json(CONFIG_FILE)

        guild_id = str(interaction.guild.id)

        if guild_id not in config:
            config[guild_id] = {}

        if "levels" not in config[guild_id]:
            config[guild_id]["levels"] = {}

        config[guild_id]["levels"][str(warn)] = action

        await self.save_json(CONFIG_FILE, config)

        embed = discord.Embed(
            title="Warn Level Set",
            description=f"{warn} warns → {action}",
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=embed)

        # =========================
    # WARN COMMAND
    # =========================

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_permissions(moderate_members=True)

    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):

        now = datetime.utcnow()

        if interaction.user.id in self.warn_cooldown:

            if now < self.warn_cooldown[interaction.user.id]:
                await interaction.response.send_message(
                    "You must wait before warning again.",
                    ephemeral=True
                )
                return

        self.warn_cooldown[interaction.user.id] = now + timedelta(seconds=10)

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)

        user_data = self.get_user_data(guild_data, member.id)

        warn_entry = {
            "moderator": interaction.user.id,
            "reason": reason,
            "time": int(now.timestamp())
        }

        user_data["warns"].append(warn_entry)

        await self.save_json(DATA_FILE, data)

        warn_count = len(user_data["warns"])

        embed = discord.Embed(
            title="User Warned",
            description=f"{member.mention} has been warned.",
            color=discord.Color.red()
        )

        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warns", value=str(warn_count))

        await interaction.response.send_message(embed=embed)

        config = await self.load_json(CONFIG_FILE)

        guild_id = str(interaction.guild.id)

        if guild_id in config and "log_channel" in config[guild_id]:

            channel = interaction.guild.get_channel(config[guild_id]["log_channel"])

            if channel:
                await channel.send(embed=embed)


    # =========================
    # REMOVE WARN
    # =========================

    @app_commands.command(name="removewarn", description="Remove a warn")
    @app_commands.checks.has_permissions(moderate_members=True)

    async def removewarn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        index: int
    ):

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)

        user_data = self.get_user_data(guild_data, member.id)

        warns = user_data["warns"]

        if index < 1 or index > len(warns):

            await interaction.response.send_message(
                "Invalid warn index.",
                ephemeral=True
            )
            return

        removed = warns.pop(index - 1)

        await self.save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="Warn Removed",
            description=f"Removed warn from {member.mention}",
            color=discord.Color.green()
        )

        embed.add_field(name="Reason", value=removed["reason"])

        await interaction.response.send_message(embed=embed)


    # =========================
    # CLEAR WARNS
    # =========================

    @app_commands.command(name="clearwarn", description="Clear all warns")
    @app_commands.checks.has_permissions(administrator=True)

    async def clearwarn(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)

        user_data = self.get_user_data(guild_data, member.id)

        user_data["warns"] = []

        await self.save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="Warns Cleared",
            description=f"All warns cleared for {member.mention}",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


    # =========================
    # WARN INFO
    # =========================

    @app_commands.command(name="warninfo", description="Check warn history")

    async def warninfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)

        user_data = self.get_user_data(guild_data, member.id)

        warns = user_data["warns"]

        if not warns:

            await interaction.response.send_message(
                "User has no warns."
            )
            return

        description = ""

        for i, w in enumerate(warns, start=1):

            t = f"<t:{w['time']}:R>"

            description += f"**{i}.** {w['reason']} • {t}\n"

        embed = discord.Embed(
            title=f"Warn History - {member}",
            description=description,
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=embed)

    # =========================
    # RESET WARNS (single user)
    # =========================

    @app_commands.command(
        name="resetwarn",
        description="Reset all warns of a member"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def resetwarn(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)
        user_data = self.get_user_data(guild_data, member.id)

        user_data["warns"] = []

        await self.save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="Warn Reset",
            description=f"All warns of {member.mention} have been reset.",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


    # =========================
    # WARN LIST (pagination)
    # =========================

    @app_commands.command(
        name="warnlist",
        description="View warn list with pagination"
    )
    async def warnlist(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        data = await self.load_json(DATA_FILE)

        guild_data = self.get_guild_data(data, interaction.guild.id)
        user_data = self.get_user_data(guild_data, member.id)

        warns = user_data["warns"]

        if not warns:

            await interaction.response.send_message(
                "This user has no warns.",
                ephemeral=True
            )
            return

        page_size = 5
        pages = []

        for i in range(0, len(warns), page_size):

            chunk = warns[i:i+page_size]

            text = ""

            for idx, w in enumerate(chunk, start=i+1):

                t = f"<t:{w['time']}:R>"

                text += f"**{idx}.** {w['reason']} • {t}\n"

            pages.append(text)

        page = 0

        embed = discord.Embed(
            title=f"Warn list - {member}",
            description=pages[page],
            color=discord.Color.orange()
        )

        msg = await interaction.response.send_message(embed=embed)

        if len(pages) == 1:
            return

        message = await interaction.original_response()

        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):

            return (
                user == interaction.user
                and str(reaction.emoji) in ["⬅️", "➡️"]
                and reaction.message.id == message.id
            )

        while True:

            try:

                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=60,
                    check=check
                )

            except asyncio.TimeoutError:
                break

            if str(reaction.emoji) == "➡️":

                if page < len(pages) - 1:
                    page += 1

            elif str(reaction.emoji) == "⬅️":

                if page > 0:
                    page -= 1

            embed.description = pages[page]

            await message.edit(embed=embed)

            await message.remove_reaction(reaction, user)


# =========================
# SETUP
# =========================

async def setup(bot):

    await bot.add_cog(WarnSystem(bot))
