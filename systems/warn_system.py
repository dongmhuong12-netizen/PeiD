import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
from datetime import timedelta

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


class WarnSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_files()

    # ================= FILE HANDLING =================

    def load_files(self):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump({}, f)

        with open(DATA_FILE, "r") as f:
            self.warn_data = json.load(f)

        with open(CONFIG_FILE, "r") as f:
            self.warn_config = json.load(f)

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.warn_data, f, indent=4)

    # ================= TIME PARSER =================

    def parse_duration(self, value: str):
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
        elif unit == "h":
            return amount * 60
        elif unit == "d":
            return amount * 60 * 24

        return None

    # ================= WARN COMMAND =================

    @app_commands.command(name="warn", description="Cảnh cáo thành viên")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in self.warn_config:
            await interaction.response.send_message("Server chưa cấu hình level.", ephemeral=True)
            return

        levels = self.warn_config[guild_id].get("levels", {})
        if not levels:
            await interaction.response.send_message("Server chưa có level nào được thiết lập.", ephemeral=True)
            return

        max_level = max(map(int, levels.keys()))

        # Init data guild
        if guild_id not in self.warn_data:
            self.warn_data[guild_id] = {}

        # Init data user
        if user_id not in self.warn_data[guild_id]:
            self.warn_data[guild_id][user_id] = {
                "level": 0,
                "last_warn": None
            }

        user_data = self.warn_data[guild_id][user_id]
        current_level = user_data["level"]
        reset_triggered = False

        now = discord.utils.utcnow()

        # ================= RESET CHECK =================
        if current_level > 0 and user_data["last_warn"]:
            level_config = levels.get(str(current_level))
            if level_config:
                reset_minutes = self.parse_duration(level_config["reset"])
                if reset_minutes:
                    last_warn_time = discord.utils.parse_time(user_data["last_warn"])
                    diff = now - last_warn_time
                    if diff >= timedelta(minutes=reset_minutes):
                        current_level = 0
                        reset_triggered = True

        # ================= LEVEL INCREASE =================
        if current_level < max_level:
            current_level += 1

        # Get new level config
        level_config = levels.get(str(current_level))
        punishment = level_config.get("punishment", "none")

        # Save data
        self.warn_data[guild_id][user_id]["level"] = current_level
        self.warn_data[guild_id][user_id]["last_warn"] = now.isoformat()
        self.save_data()

        # ================= APPLY PUNISHMENT =================
        punishment_text = "Không có"

        try:
            if punishment == "kick":
                await member.kick(reason="Warn system level reached")
                punishment_text = "Kick"

            elif punishment == "ban":
                await member.ban(reason="Warn system level reached")
                punishment_text = "Ban"

            elif punishment.startswith("timeout:"):
                duration_str = punishment.split(":")[1]
                timeout_minutes = self.parse_duration(duration_str)

                if timeout_minutes:
                    until = now + timedelta(minutes=timeout_minutes)
                    await member.timeout(until, reason="Warn system level reached")
                    punishment_text = f"Timeout {duration_str}"
                else:
                    punishment_text = "Timeout (format lỗi)"

            else:
                punishment_text = "Không có"

        except Exception:
            punishment_text = "Bot thiếu quyền hoặc lỗi khi áp dụng"

        # ================= EMBED =================
        embed = discord.Embed(
            title="WARNING | CẢNH CÁO",
            color=discord.Color.red()
        )

        embed.add_field(name="Thành viên", value=member.mention, inline=False)
        embed.add_field(name="Level hiện tại", value=str(current_level), inline=True)
        embed.add_field(name="Lý do", value=reason, inline=False)
        embed.add_field(name="Hình phạt", value=punishment_text, inline=False)

        if reset_triggered:
            embed.add_field(
                name="🔄 Reset",
                value="Level trước đó đã hết hạn và được đưa về 0 trước khi áp dụng cảnh cáo mới.",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # ================= ERROR HANDLER =================

    @warn.error
    async def warn_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("Bạn không có quyền sử dụng lệnh này.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(WarnSystem(bot))
