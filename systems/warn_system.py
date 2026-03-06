import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import re
import asyncio
from datetime import timedelta, datetime

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


class WarnGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="warn", description="Hệ thống cảnh cáo")

        self.file_lock = asyncio.Lock()

        for file in [DATA_FILE, CONFIG_FILE]:
            if not os.path.exists(file):
                with open(file, "w") as f:
                    json.dump({}, f)

    # ================= JSON =================

    def load_json(self, file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}

    async def save_json(self, file, data):
        async with self.file_lock:
            with open(file, "w") as f:
                json.dump(data, f, indent=4)

    # ================= TIME =================

    def parse_duration(self, value: str):

        if not value:
            return None

        value = value.strip().lower()

        match = re.match(r"^(\d+)([mhd])$", value)
        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)

        if amount <= 0:
            return None

        if unit == "m":
            return amount
        if unit == "h":
            return amount * 60
        if unit == "d":
            return amount * 1440

        return None

    # ================= FORMAT TIME TEXT =================

    def format_time_text(self, duration: str):

        minutes = self.parse_duration(duration)

        if not minutes:
            return duration

        if minutes < 60:
            return f"Mute {minutes} phút"
        else:
            hours = minutes // 60
            return f"Mute {hours} giờ"

    # ================= MÀU THEO LEVEL =================

    def get_level_color(self, level: int):

        if level <= 1:
            return discord.Color.green()
        elif level == 2:
            return discord.Color.yellow()
        elif level == 3:
            return discord.Color.orange()
        elif level == 4:
            return discord.Color.red()
        else:
            return discord.Color.dark_red()

    # ================= STYLE EMBED =================

    def build_embed(self, title, body, color, member=None):

        embed = discord.Embed(
            description=(
                "────────────────────\n"
                f"{title}\n"
                "────────────────────\n\n"
                f"{body}\n\n"
                "────────────────────\n"
                "HỆ THỐNG QUẢN LÝ KỶ LUẬT"
            ),
            color=color
        )

        if member:
            embed.set_thumbnail(url=member.display_avatar.url)

        embed.timestamp = discord.utils.utcnow()

        return embed

    # ================= LOG =================

    async def send_log_or_here(self, interaction, embed):

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        log_channel_id = config.get(guild_id, {}).get("log_channel")

        if log_channel_id:

            channel = interaction.guild.get_channel(log_channel_id)

            if channel:
                await channel.send(embed=embed)
                await interaction.followup.send("Done.", ephemeral=True)
                return

        await interaction.followup.send(embed=embed)

    # ================= SET LOG =================

    @app_commands.command(name="setlog", description="Thiết lập kênh log")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        config.setdefault(guild_id, {"levels": {}})
        config[guild_id]["log_channel"] = channel.id

        await self.save_json(CONFIG_FILE, config)

        await interaction.followup.send("Đã set log.", ephemeral=True)

    # ================= SET LEVEL =================

    @app_commands.command(name="setlevel", description="Thiết lập level")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlevel(self, interaction: discord.Interaction, level: int, reset: str, punishment: str):

        await interaction.response.defer(ephemeral=True)

        reset_minutes = self.parse_duration(reset)

        if reset_minutes is None:
            await interaction.followup.send("Reset sai định dạng (10m/1h/1d).", ephemeral=True)
            return

        if punishment.lower() in ["kick", "ban"]:
            punishment_value = punishment.lower()
        else:

            timeout_minutes = self.parse_duration(punishment)

            if timeout_minutes is None:
                await interaction.followup.send("Punishment không hợp lệ.", ephemeral=True)
                return

            punishment_value = f"timeout:{punishment.lower()}"

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        config.setdefault(guild_id, {"levels": {}})

        config[guild_id]["levels"][str(level)] = {
            "reset": reset.lower(),
            "punishment": punishment_value
        }

        await self.save_json(CONFIG_FILE, config)

        await interaction.followup.send(f"Đã set level {level}.", ephemeral=True)

    # ================= WARN ADD =================

    @app_commands.command(name="add", description="Cảnh cáo thành viên")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):

        await interaction.response.defer(ephemeral=True)

        try:

            if (
                member == interaction.user
                or member == interaction.guild.owner
                or member.guild_permissions.administrator
                or member.top_role >= interaction.guild.me.top_role
            ):
                await interaction.followup.send("Không thể warn người này.", ephemeral=True)
                return

            config = self.load_json(CONFIG_FILE)
            data = self.load_json(DATA_FILE)

            guild_id = str(interaction.guild.id)
            user_id = str(member.id)

            if guild_id not in config or not config[guild_id].get("levels"):
                await interaction.followup.send("Chưa cấu hình level.", ephemeral=True)
                return

            levels = config[guild_id]["levels"]
            max_level = max(map(int, levels.keys()))

            data.setdefault(guild_id, {})

            data[guild_id].setdefault(user_id, {
                "level": 0,
                "last_warn": None,
                "reset_at": None,
                "history": []
            })

            user_data = data[guild_id][user_id]

            now = discord.utils.utcnow()

            if user_data.get("reset_at"):

                try:
                    reset_time = datetime.fromisoformat(user_data["reset_at"])
                except:
                    reset_time = None

                if reset_time and now >= reset_time:
                    user_data["level"] = 0
                    user_data["reset_at"] = None

            new_level = min(user_data["level"] + 1, max_level)

            level_config = levels.get(str(new_level))

            if not level_config:
                await interaction.followup.send(
                    f"Level {new_level} chưa được cấu hình.",
                    ephemeral=True
                )
                return

            punishment_raw = level_config["punishment"]

       # ================= WARN REMOVE =================

    @app_commands.command(name="remove", description="Giảm level cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:

            await interaction.followup.send(
                "Người này chưa có cảnh cáo.",
                ephemeral=True
            )
            return

        user_data = data[guild_id][user_id]

        if user_data["level"] <= 0:

            await interaction.followup.send(
                "Level đã bằng 0.",
                ephemeral=True
            )
            return

        user_data["level"] -= 1

        if user_data["level"] == 0:
            user_data["reset_at"] = None

        await self.save_json(DATA_FILE, data)

        body = (
            f"• ĐỐI TƯỢNG: {member.mention}\n"
            f"• LEVEL HIỆN TẠI: {user_data['level']}"
        )

        embed = self.build_embed(
            "WARN REMOVED",
            body,
            discord.Color.green(),
            member
        )

        await self.send_log_or_here(interaction, embed)


# ================= WARN CLEAR =================

    @app_commands.command(name="clear", description="Xóa toàn bộ cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id in data and user_id in data[guild_id]:

            del data[guild_id][user_id]

            await self.save_json(DATA_FILE, data)

        embed = self.build_embed(
            "WARN CLEARED",
            f"Đã xóa toàn bộ cảnh cáo của {member.mention}.",
            discord.Color.green(),
            member
        )

        await self.send_log_or_here(interaction, embed)


# ================= WARN INFO =================

    @app_commands.command(name="info", description="Xem thông tin cảnh cáo")
    async def info(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:

            embed = self.build_embed(
                "WARN INFO",
                f"{member.mention} không có cảnh cáo.",
                discord.Color.green(),
                member
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

            return

        user_data = data[guild_id][user_id]

        level = user_data.get("level", 0)

        reset_text = "Không có"

        if user_data.get("reset_at"):

            try:

                reset_time = datetime.fromisoformat(user_data["reset_at"])

                reset_text = f"<t:{int(reset_time.timestamp())}:R>"

            except:
                reset_text = "Không xác định"

        body = (
            f"• THÀNH VIÊN: {member.mention}\n"
            f"• LEVEL: {level}\n"
            f"• RESET: {reset_text}\n"
            f"• SỐ LẦN WARN: {len(user_data.get('history', []))}"
        )

        embed = self.build_embed(
            "WARN INFO",
            body,
            self.get_level_color(level),
            member
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


# ================= SETUP =================

async def setup(bot: commands.Bot):

    warn_group = WarnGroup()

    bot.tree.add_command(warn_group)     
