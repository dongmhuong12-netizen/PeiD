import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import re
from datetime import timedelta, datetime

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


# ==============================
# WARN COMMAND GROUP
# ==============================

class WarnGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="warn", description="Hệ thống cảnh cáo")

        for file in [DATA_FILE, CONFIG_FILE]:
            if not os.path.exists(file):
                with open(file, "w") as f:
                    json.dump({}, f)

    # ========= JSON =========

    def load_json(self, file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ========= TIME =========

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

    # ========= SET LOG =========

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

    # ========= SET LEVEL =========

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

    # ========= WARN ADD =========

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
        data[guild_id].setdefault(user_id, {
            "level": 0,
            "last_warn": None,
            "reset_at": None
        })

        user_data = data[guild_id][user_id]
        current_level = user_data["level"]
        now = discord.utils.utcnow()

        # check auto reset cũ
        reset_at = user_data.get("reset_at")
        if reset_at:
            reset_time = datetime.fromisoformat(reset_at)
            if now >= reset_time:
                current_level = 0

        new_level = min(current_level + 1, max_level)
        level_config = levels[str(new_level)]
        punishment = level_config["punishment"]

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

        reset_minutes = self.parse_duration(level_config["reset"])
        reset_time = now + timedelta(minutes=reset_minutes)

        user_data["level"] = new_level
        user_data["last_warn"] = now.isoformat()
        user_data["reset_at"] = reset_time.isoformat()

        self.save_json(DATA_FILE, data)

        await interaction.followup.send(
            f"{member.mention} đã bị warn. Level hiện tại: {new_level}"
        )

    # ========= WARN REMOVE =========

    @app_commands.command(name="remove")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove(self, interaction: discord.Interaction, member: discord.Member, amount: int = 1):
        await interaction.response.defer(ephemeral=True)

        if amount <= 0:
            await interaction.followup.send("Amount phải lớn hơn 0.", ephemeral=True)
            return

        data = self.load_json(DATA_FILE)
        config = self.load_json(CONFIG_FILE)

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
        now = discord.utils.utcnow()

        data[guild_id][user_id]["level"] = new_level
        data[guild_id][user_id]["last_warn"] = now.isoformat()

        if new_level > 0:
            levels = config[guild_id]["levels"]
            level_config = levels.get(str(new_level))
            if level_config:
                reset_minutes = self.parse_duration(level_config["reset"])
                reset_time = now + timedelta(minutes=reset_minutes)
                data[guild_id][user_id]["reset_at"] = reset_time.isoformat()
        else:
            data[guild_id][user_id]["reset_at"] = None

        self.save_json(DATA_FILE, data)

        await interaction.followup.send(
            f"Đã giảm warn của {member.mention} từ {current_level} xuống {new_level}.",
            ephemeral=True
        )

    # ========= WARN RESET =========

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
            data[guild_id][user_id]["reset_at"] = None
            self.save_json(DATA_FILE, data)

        await interaction.followup.send(f"Đã reset warn của {member.mention}.", ephemeral=True)

    # ========= WARN INFO =========

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


# ==============================
# AUTO RESET BACKGROUND
# ==============================

class WarnBackground(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_reset.start()

    @tasks.loop(minutes=1)
    async def auto_reset(self):
        if not os.path.exists(DATA_FILE):
            return

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        now = discord.utils.utcnow()
        changed = False

        for guild_id, guild_data in data.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            log_channel_id = config.get(guild_id, {}).get("log_channel")
            channel = guild.get_channel(log_channel_id) if log_channel_id else None

            for user_id, user_data in guild_data.items():
                reset_at = user_data.get("reset_at")
                if not reset_at:
                    continue

                reset_time = datetime.fromisoformat(reset_at)
                if now >= reset_time and user_data["level"] > 0:
                    old_level = user_data["level"]
                    user_data["level"] = 0
                    user_data["reset_at"] = None
                    changed = True

                    if channel:
                        member = guild.get_member(int(user_id))
                        if member:
                            embed = discord.Embed(
                                title="AUTO RESET | HẾT THỜI GIAN",
                                description=(
                                    f"• ĐỐI TƯỢNG: {member.mention}\n"
                                    f"• LEVEL: {old_level} → 0\n"
                                    f"• LÝ DO: Hết thời gian reset\n"
                                    f"• TRẠNG THÁI: ĐÃ TRẮNG ÁN"
                                ),
                                color=discord.Color.green()
                            )
                            embed.set_footer(text="HỆ THỐNG QUẢN LÝ KỶ LUẬT")
                            await channel.send(embed=embed)

        if changed:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)


# ==============================
# SETUP
# ==============================

async def setup(bot):
    bot.tree.add_command(WarnGroup())
    await bot.add_cog(WarnBackground(bot))
