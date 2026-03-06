import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime, timedelta

DATA_FILE = "data/warn_data.json"
CONFIG_FILE = "data/warn_config.json"

MAX_HISTORY = 50

file_lock = asyncio.Lock()


# =========================
# JSON LOAD
# =========================

def load_json(file):

    if not os.path.exists(file):
        return {}

    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# =========================
# JSON SAVE
# =========================

async def save_json(file, data):

    os.makedirs("data", exist_ok=True)

    async with file_lock:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


# =========================
# TIME FORMAT
# =========================

def format_duration(minutes):

    if minutes < 60:
        return f"{minutes} phút"

    hours = minutes // 60

    if hours < 24:
        return f"{hours} giờ"

    days = hours // 24

    return f"{days} ngày"


# =========================
# WARN SYSTEM
# =========================

class WarnSystem(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

        self.data_cache = load_json(DATA_FILE)
        self.config_cache = load_json(CONFIG_FILE)


# =========================
# DATA ACCESS
# =========================

    def get_guild_data(self, guild_id):

        guild_id = str(guild_id)

        if guild_id not in self.data_cache:
            self.data_cache[guild_id] = {}

        return self.data_cache[guild_id]


    def get_config(self, guild_id):

        guild_id = str(guild_id)

        if guild_id not in self.config_cache:
            self.config_cache[guild_id] = {}

        return self.config_cache[guild_id]


# =========================
# SAVE CACHE
# =========================

    async def save_data(self):

        await save_json(DATA_FILE, self.data_cache)


    async def save_config(self):

        await save_json(CONFIG_FILE, self.config_cache)


# =========================
# LOG FUNCTION
# =========================

    async def send_log_or_here(self, interaction, embed):

        config = self.get_config(interaction.guild.id)

        log_channel_id = config.get("log_channel")

        if log_channel_id:

            channel = interaction.guild.get_channel(int(log_channel_id))

            if channel:
                try:
                    await channel.send(embed=embed)
                    return
                except discord.Forbidden:
                    pass

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

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

        await interaction.response.defer(ephemeral=True)

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

            level_config = levels.get(str(new_level))

            if not level_config:
                await interaction.followup.send(
                    f"Level {new_level} chưa được cấu hình.",
                    ephemeral=True
                )
                return

            punishment_raw = level_config["punishment"]

            try:

                if punishment_raw == "kick":

                    await member.kick(reason="Warn system")
                    punishment_text = "Kick"

                elif punishment_raw == "ban":

                    await member.ban(reason="Warn system")
                    punishment_text = "Ban"

                elif punishment_raw.startswith("timeout:"):

                    duration_str = punishment_raw.split(":")[1]

                    timeout_minutes = self.parse_duration(duration_str)

                    if timeout_minutes:

                        await member.timeout(now + timedelta(minutes=timeout_minutes))
                        punishment_text = self.format_time_text(duration_str)

                    else:
                        punishment_text = punishment_raw

                else:
                    punishment_text = punishment_raw

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

            body = (
                f"• CẤP ĐỘ: LEVEL {new_level}\n"
                f"• ĐỐI TƯỢNG: {member.mention}\n"
                f"• HÌNH PHẠT: {punishment_text}\n\n"
                "LÝ DO\n"
                f"{reason}\n\n"
                f"• RESET: {reset_text}"
            )

            embed = self.build_embed(
                "WARNING | CẢNH CÁO",
                body,
                self.get_level_color(new_level),
                member
            )

            await self.send_log_or_here(interaction, embed)

        except Exception as e:

            await interaction.followup.send(
                f"Lỗi hệ thống: {e}",
                ephemeral=True
            )

# ================= WARN REMOVE =================

    @app_commands.command(name="remove", description="Giảm level cảnh cáo")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(ephemeral=True)

        data = self.load_json(DATA_FILE)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in data or user_id not in data[guild_id]:
            await interaction.followup.send("Người này chưa có warn.", ephemeral=True)
            return

        user_data = data[guild_id][user_id]

        if user_data["level"] <= 0:
            await interaction.followup.send("Level đã bằng 0.", ephemeral=True)
            return

        user_data["level"] -= 1

        if user_data["level"] == 0:
            user_data["reset_at"] = None

        self.save_json(DATA_FILE, data)

        body = (
            f"• ĐỐI TƯỢNG: {member.mention}\n"
            f"• LEVEL HIỆN TẠI: {user_data['level']}"
        )

        embed = self.build_embed(
            "WARN REMOVED",
            body,
            0x57F287,
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
            self.save_json(DATA_FILE, data)

        embed = self.build_embed(
            "WARN CLEARED",
            f"Đã xóa toàn bộ cảnh cáo của {member.mention}.",
            0x57F287,
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
                0x57F287,
                member
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        user_data = data[guild_id][user_id]

        level = user_data.get("level", 0)

        reset_text = "Không có"

        if user_data.get("reset_at"):
            reset_time = datetime.fromisoformat(user_data["reset_at"])
            reset_text = f"<t:{int(reset_time.timestamp())}:R>"

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
    await bot.add_cog(WarnGroup(bot))
