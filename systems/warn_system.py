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

    # ================= FILE =================

    def load_json(self, file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ================= TIME =================

    def parse_duration(self, value: str):
        if not value:
            return None

        match = re.match(r"^(\d+)([mhd])$", value.lower())
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

    # ================= SET LOG =================

    @app_commands.command(name="setlog")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        config = self.load_json(CONFIG_FILE)
        guild_id = str(interaction.guild.id)

        config.setdefault(guild_id, {"levels": {}})
        config[guild_id]["log_channel"] = channel.id

        self.save_json(CONFIG_FILE, config)
        await interaction.followup.send("Đã thiết lập kênh log.", ephemeral=True)

    # ================= SET LEVEL =================

    @app_commands.command(name="setlevel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setlevel(self, interaction: discord.Interaction, level: int, reset: str, punishment: str):
        await interaction.response.defer(ephemeral=True)

        reset_minutes = self.parse_duration(reset)
        if reset_minutes is None:
            await interaction.followup.send("Reset không hợp lệ (10m / 1h / 1d).", ephemeral=True)
            return

        if punishment.lower() in ["kick", "ban"]:
            punishment_value = punishment.lower()
        else:
            timeout_minutes = self.parse_duration(punishment)
            if timeout_minutes is None:
                await interaction.followup.send("Hình phạt không hợp lệ.", ephemeral=True)
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
        await interaction.followup.send(f"Đã thiết lập level {level}.", ephemeral=True)

    # ================= WARN ADD =================

    @app_commands.command(name="add")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        await interaction.response.defer()

        if (
            member == interaction.guild.owner
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
            await interaction.followup.send("Server chưa cấu hình level.", ephemeral=True)
            return

        levels = config[guild_id]["levels"]
        max_level = max(map(int, levels.keys()))

        data.setdefault(guild_id, {})
        data[guild_id].setdefault(user_id, {"level": 0, "last_warn": None})

        user_data = data[guild_id][user_id]
        current_level = user_data["level"]
        now = discord.utils.utcnow()

        # RESET CHECK
        if current_level > 0 and user_data["last_warn"]:
            level_config = levels.get(str(current_level))
            if level_config:
                reset_minutes = self.parse_duration(level_config["reset"])
                last_warn_time = discord.utils.parse_time(user_data["last_warn"])
                if reset_minutes and now - last_warn_time >= timedelta(minutes=reset_minutes):
                    current_level = 0

        new_level = min(current_level + 1, max_level)
        punishment = levels[str(new_level)]["punishment"]

        try:
            if punishment == "kick":
                await member.kick(reason="Warn system")
            elif punishment == "ban":
                await member.ban(reason="Warn system")
            elif punishment.startswith("timeout:"):
                duration_str = punishment.split(":")[1]
                timeout_minutes = self.parse_duration(duration_str)
                if timeout_minutes:
                    until = now + timedelta(minutes=timeout_minutes)
                    await member.timeout(until)
        except:
            await interaction.followup.send("Bot thiếu quyền để thực hiện hình phạt.", ephemeral=True)
            return

        data[guild_id][user_id]["level"] = new_level
        data[guild_id][user_id]["last_warn"] = now.isoformat()
        self.save_json(DATA_FILE, data)

        await interaction.followup.send(f"{member.mention} đã bị warn. Level hiện tại: {new_level}")

    # ================= WARN REMOVE =================

    @app_commands.command(name="remove")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove(self, interaction: discord.Interaction, member: discord.Member, amount: int = 1):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            await interaction.followup.send("Amount phải lớn hơn 0.", ephemeral=True)
            return

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:
            await interaction.followup.send("Người này không có warn.", ephemeral=True)
            return

        current_level = data[guild_id][user_id]["level"]
        if current_level <= 0:
            await interaction.followup.send("Người này không có warn.", ephemeral=True)
            return

        new_level = max(current_level - amount, 0)

        data[guild_id][user_id]["level"] = new_level
        data[guild_id][user_id]["last_warn"] = discord.utils.utcnow().isoformat()

        self.save_json(DATA_FILE, data)

        await interaction.followup.send(
            f"Đã giảm warn của {member.mention} từ {current_level} xuống {new_level}.",
            ephemeral=True
        )

    # ================= WARN RESET =================

    @app_commands.command(name="reset")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id in data and user_id in data[guild_id]:
            data[guild_id][user_id]["level"] = 0
            data[guild_id][user_id]["last_warn"] = None
            self.save_json(DATA_FILE, data)

        await interaction.followup.send(f"Đã reset warn của {member.mention}.", ephemeral=True)

    # ================= WARN INFO =================

    @app_commands.command(name="info")
    async def info(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        level = 0
        if guild_id in data and user_id in data[guild_id]:
            level = data[guild_id][user_id]["level"]

        await interaction.followup.send(
            f"{member.mention} hiện đang ở level warn: {level}",
            ephemeral=True
        )


async def setup(bot):
    pass
