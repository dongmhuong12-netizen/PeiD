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
        await interaction.response.defer(ephemeral=True)

        reset_minutes = self.parse_duration(reset)
        if reset_minutes is None:
            await interaction.followup.send(
                "Reset không hợp lệ. Ví dụ: 10m / 1h / 1d",
                ephemeral=True
            )
            return

        punishment_value = None

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
            punishment_value = f"timeout:{punishment}"

        guild_id = str(interaction.guild.id)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        if guild_id not in config:
            config[guild_id] = {"levels": {}}

        config[guild_id]["levels"][str(level)] = {
            "reset": reset,
            "punishment": punishment_value
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

        await interaction.followup.send(
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
        await interaction.response.defer()

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        if guild_id not in config or not config[guild_id]["levels"]:
            await interaction.followup.send(
                "Server chưa cấu hình level.",
                ephemeral=True
            )
            return

        levels = config[guild_id]["levels"]
        max_level = max(map(int, levels.keys()))

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

       
