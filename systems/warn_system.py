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

        for file in [DATA_FILE, CONFIG_FILE]:
            if not os.path.exists(file):
                with open(file, "w") as f:
                    json.dump({}, f)

    # ================= FILE HELPERS =================

    def load_json(self, file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ================= TIME PARSER =================

    def parse_duration(self, value: str):
        if not value:
            return None

        pattern = r"^(\d+)([mhd])$"
        match = re.match(pattern, value.lower())

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

    # ================= SET LOG CHANNEL =================

    @app_commands.command(name="setlog", description="Thiết lập kênh log cho warn")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        config.setdefault(guild_id, {"levels": {}})
        config[guild_id]["log_channel"] = channel.id

        self.save_json(CONFIG_FILE, config)

        await interaction.followup.send(
            f"Đã thiết lập kênh log: {channel.mention}",
            ephemeral=True
        )

    # ================= SET LEVEL =================

    @app_commands.command(name="setlevel", description="Thiết lập level cảnh cáo")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlevel(self, interaction: discord.Interaction, level: int, reset: str, punishment: str):
        await interaction.response.defer(ephemeral=True)

        reset_minutes = self.parse_duration(reset)
        if reset_minutes is None:
            await interaction.followup.send(
                "Reset không hợp lệ. Ví dụ: 10m / 1h / 1d",
                ephemeral=True
            )
            return

        if punishment.lower() in ["kick", "ban"]:
            punishment_value = punishment.lower()
        else:
            timeout_minutes = self.parse_duration(punishment)
            if timeout_minutes is None:
                await interaction.followup.send(
                    "Hình phạt không hợp lệ. Nhập: kick / ban / 5m / 1h / 1d",
                    ephemeral=True
                )
                return
            punishment_value = f"timeout:{punishment.lower()}"

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        config.setdefault(guild_id, {"levels": {}})
        config[guild_id]["levels"][str(level)] = {
            "reset": reset.lower(),
            "punishment": punishment_value
        }

        self.save_json(CONFIG_FILE, config)

        await interaction.followup.send(
            f"Đã thiết lập level {level}.",
            ephemeral=True
        )

    # ================= WARN ADD =================

    @app_commands.command(name="add", description="Cảnh cáo thành viên")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        await interaction.response.defer()

        # ===== CHECK KHÔNG CHO WARN =====
        if (
            member == interaction.guild.owner
            or member.guild_permissions.administrator
            or member.top_role >= interaction.guild.me.top_role
        ):
            await interaction.followup.send(
                "Không thể warn. Người bị warn có quyền quản lí hoặc cao hơn bot.",
                ephemeral=True
            )
            return

        config = self.load_json(CONFIG_FILE)
        data = self.load_json(DATA_FILE)

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in config or not config[guild_id].get("levels"):
            await interaction.followup.send(
                "Server chưa cấu hình level.",
                ephemeral=True
            )
            return

        levels = config[guild_id]["levels"]
        max_level = max(map(int, levels.keys()))

        data.setdefault(guild_id, {})
        data[guild_id].setdefault(user_id, {"level": 0, "last_warn": None})

        user_data = data[guild_id][user_id]
        current_level = user_data["level"]
        now = discord.utils.utcnow()

        # ===== RESET CHECK =====
        if current_level > 0 and user_data["last_warn"]:
            level_config = levels.get(str(current_level))
            if level_config:
                reset_minutes = self.parse_duration(level_config["reset"])
                last_warn_time = discord.utils.parse_time(user_data["last_warn"])

                if reset_minutes and now - last_warn_time >= timedelta(minutes=reset_minutes):
                    current_level = 0

        new_level = min(current_level + 1, max_level)
        level_config = levels[str(new_level)]
        punishment = level_config["punishment"]

        punishment_text = "Không có"

        # ===== THỰC HIỆN HÌNH PHẠT =====
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

        except:
            await interaction.followup.send(
                "Không thể warn, nhập sai số hoặc người bị warn có quyền quản lí.",
                ephemeral=True
            )
            return

        # ===== SAVE CHỈ KHI THÀNH CÔNG =====
        data[guild_id][user_id]["level"] = new_level
        data[guild_id][user_id]["last_warn"] = now.isoformat()
        self.save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="WARNING",
            description="**HỆ THỐNG QUẢN LÝ KỶ LUẬT**",
            color=discord.Color.red()
        )

        embed.add_field(name="Thành viên", value=member.mention, inline=False)
        embed.add_field(name="Level", value=str(new_level))
        embed.add_field(name="Lý do", value=reason, inline=False)
        embed.add_field(name="Hình phạt", value=punishment_text, inline=False)

        log_channel_id = config[guild_id].get("log_channel")

        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
                await interaction.followup.send("Đã xử lý cảnh cáo.", ephemeral=True)
                return

        await interaction.followup.send(embed=embed)


# ⚠️ QUAN TRỌNG: KHÔNG ADD COMMAND Ở ĐÂY
async def setup(bot):
    pass
