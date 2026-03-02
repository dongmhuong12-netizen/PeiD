import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import re
from datetime import timedelta, datetime

DATA_FILE = "warn_data.json"
CONFIG_FILE = "warn_config.json"


class WarnGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="warn", description="Hệ thống cảnh cáo")

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

        self.save_json(CONFIG_FILE, config)
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

        self.save_json(CONFIG_FILE, config)
        await interaction.followup.send(f"Đã set level {level}.", ephemeral=True)

    # ================= WARN ADD =================

@app_commands.command(name="add", description="Cảnh cáo thành viên")
@app_commands.checks.has_permissions(manage_messages=True)
async def add(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):

    await interaction.response.defer()

    try:

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
            reset_time = datetime.fromisoformat(user_data["reset_at"])
            if now >= reset_time:
                user_data["level"] = 0
                user_data["reset_at"] = None

        new_level = min(user_data["level"] + 1, max_level)
        level_config = levels[str(new_level)]
        punishment_raw = level_config["punishment"]

        if punishment_raw in ["kick", "ban"]:
            punishment_text = punishment_raw.capitalize()
        elif punishment_raw.startswith("timeout:"):
            duration_str = punishment_raw.split(":")[1]
            punishment_text = self.format_time_text(duration_str)
        else:
            punishment_text = punishment_raw

        try:
            if punishment_raw == "kick":
                await member.kick(reason="Warn system")
            elif punishment_raw == "ban":
                await member.ban(reason="Warn system")
            elif punishment_raw.startswith("timeout:"):
                duration_str = punishment_raw.split(":")[1]
                timeout_minutes = self.parse_duration(duration_str)
                if timeout_minutes:
                    await member.timeout(now + timedelta(minutes=timeout_minutes))
        except:
            await interaction.followup.send("Bot thiếu quyền.", ephemeral=True)
            return

        reset_minutes = self.parse_duration(level_config["reset"])

        user_data["level"] = new_level
        user_data["last_warn"] = now.isoformat()
        user_data["reset_at"] = (now + timedelta(minutes=reset_minutes)).isoformat()

        user_data["history"].append({
            "level": new_level,
            "reason": reason,
            "moderator": interaction.user.id,
            "time": now.isoformat()
        })

        self.save_json(DATA_FILE, data)

        reset_time = datetime.fromisoformat(user_data["reset_at"])
        reset_text = f"<t:{int(reset_time.timestamp())}:R>"

        next_level = min(new_level + 1, max_level)
        next_config = levels.get(str(next_level))

        if next_config:
            next_punishment_raw = next_config["punishment"]

            if next_punishment_raw.startswith("timeout:"):
                duration_str = next_punishment_raw.split(":")[1]
                next_punishment_text = self.format_time_text(duration_str)
            else:
                next_punishment_text = next_punishment_raw.capitalize()

            next_reset_minutes = self.parse_duration(next_config["reset"])
            next_reset_text = (
                self.format_time_text(next_reset_minutes)
                if next_reset_minutes else "Không có"
            )

            body = (
                f"• CẤP ĐỘ: LEVEL {new_level}\n"
                f"• ĐỐI TƯỢNG: {member.mention}\n"
                f"• HÌNH PHẠT: {punishment_text}\n\n"
                "LÝ DO\n"
                f"{reason}\n\n"
                f"• RESET: {reset_text}\n"
                f"• NẾU TÁI PHẠM KHI CHƯA HẾT RESET:\n"
                f"LEVEL {next_level}\n"
                f"Hình phạt: {next_punishment_text}\n"
                f"Reset: {next_reset_text}"
            )

            embed = self.build_embed(
                "WARNING | CẢNH CÁO",
                body,
                self.get_level_color(new_level),
                member
            )

            await self.send_log_or_here(interaction, embed)

    except Exception as e:
        await interaction.followup.send(f"Lỗi hệ thống: {e}", ephemeral=True)
                # ================= WARN REMOVE =================

    @app_commands.command(name="remove", description="Giảm 1 cấp cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove(self, interaction, member: discord.Member):
        await interaction.response.defer()

        config = self.load_json(CONFIG_FILE)
        data = self.load_json(DATA_FILE)

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:
            await interaction.followup.send("Chưa có cảnh cáo.", ephemeral=True)
            return

        user_data = data[guild_id][user_id]

        if user_data["level"] <= 0:
            await interaction.followup.send("Không thể giảm thêm.", ephemeral=True)
            return

        user_data["level"] -= 1
        new_level = user_data["level"]
        now = discord.utils.utcnow()

        if new_level == 0:
            user_data["reset_at"] = None
            reset_text = "Không có"
        else:
            levels = config.get(guild_id, {}).get("levels", {})
            level_config = levels.get(str(new_level))

            if level_config:
                reset_minutes = self.parse_duration(level_config["reset"])
                if reset_minutes:
                    new_reset_time = now + timedelta(minutes=reset_minutes)
                    user_data["reset_at"] = new_reset_time.isoformat()
                    reset_text = f"<t:{int(new_reset_time.timestamp())}:R>"
                else:
                    reset_text = "Không có"
            else:
                reset_text = "Không có"

        self.save_json(DATA_FILE, data)

        body = (
            f"• CẤP ĐỘ MỚI: LEVEL {new_level}\n"
            f"• ĐỐI TƯỢNG: {member.mention}\n"
            f"• RESET MỚI: {reset_text}"
        )

        embed = self.build_embed(
            "REMOVE | GIẢM CẤP CẢNH CÁO",
            body,
            self.get_level_color(new_level),
            member
        )

        await self.send_log_or_here(interaction, embed)

    # ================= WARN CLEAR =================

    @app_commands.command(name="clear", description="Xóa toàn bộ cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:
            await interaction.followup.send("Chưa có cảnh cáo.", ephemeral=True)
            return

        data[guild_id][user_id] = {
            "level": 0,
            "last_warn": None,
            "reset_at": None,
            "history": []
        }

        self.save_json(DATA_FILE, data)

        try:
            if member.timed_out_until:
                await member.timeout(None)
        except:
            await interaction.followup.send("Bot thiếu quyền để gỡ mute.", ephemeral=True)
            return

        body = (
            f"• CẤP ĐỘ HIỆN TẠI: LEVEL 0\n"
            f"• ĐỐI TƯỢNG: {member.mention}\n"
            f"• ĐÃ GỠ MUTE (nếu có)"
        )

        embed = self.build_embed(
            "CLEAR | XÓA TOÀN BỘ CẢNH CÁO",
            body,
            discord.Color.green(),
            member
        )

        await self.send_log_or_here(interaction, embed)

    # ================= WARN INFO =================

    @app_commands.command(name="info", description="Xem thông tin cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def info(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:
            await interaction.followup.send("Chưa có cảnh cáo.", ephemeral=True)
            return

        user_data = data[guild_id][user_id]

        level = user_data.get("level", 0)
        reset_at = user_data.get("reset_at")
        history = user_data.get("history", [])

        reset_text = "Không có"
        if reset_at:
            reset_time = datetime.fromisoformat(reset_at)
            reset_text = f"<t:{int(reset_time.timestamp())}:R>"

        history_text = ""
        for h in history[-5:]:
            t = datetime.fromisoformat(h["time"])
            history_text += f"Level {h['level']} | <t:{int(t.timestamp())}:R>\n"

        body = (
            f"• CẤP ĐỘ HIỆN TẠI: LEVEL {level}\n"
            f"• ĐỐI TƯỢNG: {member.mention}\n\n"
            "LỊCH SỬ GẦN NHẤT\n"
            f"{history_text or 'Không có'}\n\n"
            f"• RESET: {reset_text}"
        )

        embed = self.build_embed(
            "WARNING | THÔNG TIN CẢNH CÁO",
            body,
            self.get_level_color(level),
            member
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


class WarnBackground(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_reset.start()

    @tasks.loop(minutes=5)
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
                if user_data.get("reset_at"):
                    reset_time = datetime.fromisoformat(user_data["reset_at"])

                    if now >= reset_time and user_data["level"] > 0:
                        member = guild.get_member(int(user_id))

                        user_data["level"] = 0
                        user_data["reset_at"] = None
                        changed = True

                        if channel and member:
                            body = f"{member.mention} đã hết thời gian cảnh cáo."
                            embed = discord.Embed(
                                description=(
                                    "────────────────────\n"
                                    "AUTO RESET\n"
                                    "────────────────────\n\n"
                                    f"{body}\n\n"
                                    "────────────────────\n"
                                    "HỆ THỐNG QUẢN LÝ KỶ LUẬT"
                                ),
                                color=discord.Color.green()
                            )
                            embed.set_thumbnail(url=member.display_avatar.url)
                            embed.timestamp = now
                            await channel.send(embed=embed)

        if changed:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)


async def setup(bot):
    await bot.add_cog(WarnBackground(bot))

