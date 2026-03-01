import discord
from discord import app_commands
import json
import os
import re
from datetime import timedelta

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


class WarnGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="warn", description="Hệ thống cảnh cáo")

        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump({}, f)

    # ================= TIME PARSER =================

    def parse_duration(self, value: str):
        pattern = r"^(\d+)([mhd])$"
        match = re.match(pattern.lower(), value.lower()) if value else None

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
            return amount * 60 * 24

        return None

    # ================= SETLEVEL =================

    @app_commands.command(name="setlevel", description="Thiết lập level cảnh cáo")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlevel(
        self,
        interaction: discord.Interaction,
        level: int,
        reset: str,
        punishment: str
    ):
        reset_minutes = self.parse_duration(reset)
        if reset_minutes is None:
            await interaction.response.send_message(
                "Reset không hợp lệ. Ví dụ: 10m / 1h / 1d",
                ephemeral=True
            )
            return

        if punishment.startswith("timeout:"):
            timeout_value = punishment.split(":")[1]
            if self.parse_duration(timeout_value) is None:
                await interaction.response.send_message(
                    "Timeout không hợp lệ. Ví dụ: timeout:30m",
                    ephemeral=True
                )
                return

        guild_id = str(interaction.guild.id)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        if guild_id not in config:
            config[guild_id] = {"levels": {}}

        config[guild_id]["levels"][str(level)] = {
            "reset": reset,
            "punishment": punishment
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

        await interaction.response.send_message(
            f"Đã thiết lập level {level}.",
            ephemeral=True
        )

    # ================= WARN ADD =================

    @app_commands.command(name="add", description="Cảnh cáo thành viên")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Không có lý do"
    ):
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        if guild_id not in config:
            await interaction.response.send_message(
                "Server chưa cấu hình level.",
                ephemeral=True
            )
            return

        levels = config[guild_id]["levels"]
        if not levels:
            await interaction.response.send_message(
                "Chưa có level nào.",
                ephemeral=True
            )
            return

        max_level = max(map(int, levels.keys()))

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        if guild_id not in data:
            data[guild_id] = {}

        if user_id not in data[guild_id]:
            data[guild_id][user_id] = {
                "level": 0,
                "last_warn": None
            }

        user_data = data[guild_id][user_id]
        current_level = user_data["level"]
        now = discord.utils.utcnow()
        reset_triggered = False

        if current_level > 0 and user_data["last_warn"]:
            level_config = levels.get(str(current_level))
            reset_minutes = self.parse_duration(level_config["reset"])
            last_warn_time = discord.utils.parse_time(user_data["last_warn"])

            if now - last_warn_time >= timedelta(minutes=reset_minutes):
                current_level = 0
                reset_triggered = True

        if current_level < max_level:
            current_level += 1

        level_config = levels[str(current_level)]
        punishment = level_config["punishment"]

        data[guild_id][user_id]["level"] = current_level
        data[guild_id][user_id]["last_warn"] = now.isoformat()

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        punishment_text = "Không có"

        try:
            if punishment == "kick":
                await member.kick(reason="Warn system")
                punishment_text = "Kick"

            elif punishment == "ban":
                await member.ban(reason="Warn system")
                punishment_text = "Ban"

            elif punishment.startswith("timeout:"):
                duration_str = punishment.split(":")[1]
                timeout_minutes = self.parse_duration(duration_str)

                if timeout_minutes:
                    until = now + timedelta(minutes=timeout_minutes)
                    await member.timeout(until)
                    punishment_text = f"Timeout {duration_str}"

        except Exception:
            punishment_text = "Bot thiếu quyền hoặc lỗi"

        embed = discord.Embed(
            title="WARNING",
            description="**HỆ THỐNG QUẢN LÝ KỶ LUẬT**",
            color=discord.Color.red()
        )

        embed.add_field(name="Thành viên", value=member.mention, inline=False)
        embed.add_field(name="Level", value=str(current_level))
        embed.add_field(name="Lý do", value=reason, inline=False)
        embed.add_field(name="Hình phạt", value=punishment_text, inline=False)

        if reset_triggered:
            embed.add_field(
                name="Reset",
                value="Level cũ đã hết hạn và được reset.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    pass
