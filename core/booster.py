import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks
from collections import defaultdict # [VÁ LỖI]

# Import các công cụ quản lý bộ nhớ
from core.cache_manager import get_raw, mark_dirty, save
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
# [VÁ LỖI] Sử dụng API chuẩn để đảm bảo Lock và trí nhớ đồng nhất
from core.booster_storage import get_levels, get_guild_config, save_guild_config
from core.state import State 
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

FILE_KEY = "booster_levels"

# ======================
# BOOST GROUP (Logic chính)
# ======================

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="boost", description="hệ thống quản lý server boost")
        self.active_editors = {}

    @app_commands.command(name="lv_create", description="mở bảng thiết kế booster level")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_create(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild
        
        # [VÁ LỖI] Dọn dẹp View cũ để giải phóng RAM trước khi nạp View mới
        if guild.id in self.active_editors:
            try: self.active_editors[guild.id].stop()
            except: pass

        # PHẢI AWAIT: Lấy cấu hình đã lưu
        config = await get_guild_config(guild.id)
        booster_role_id = config.get("booster_role")

        if not booster_role_id:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} aree... cậu hãy thiết lập `booster role` trước bằng `/p boost role` nhé",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed)

        from core.booster_level_ui import BoosterLevelView
        levels = await get_levels(guild.id) or [{"role": str(booster_role_id), "days": 0}]
        
        view = BoosterLevelView(guild_id=guild.id, booster_role=booster_role_id, levels=levels)
        view.timeout = 600 
        embed = view.build_embed()
        
        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg
        self.active_editors[guild.id] = view

    @app_commands.command(name="lv_channel", description="đặt kênh thông báo level boost")
    async def lv_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # [VÁ LỖI] Sử dụng API lưu trữ chuẩn để tránh Race Condition
        config = await get_guild_config(interaction.guild.id)
        config["lv_channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"đặt kênh `level boost` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="lv_message", description="đặt nội dung thông báo level boost")
    async def lv_message(self, interaction: discord.Interaction, text: str):
        config = await get_guild_config(interaction.guild.id)
        config["lv_message"] = text
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung `level boost` thành công: `{text}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="lv_embed", description="gán embed cho level boost")
    async def lv_embed(self, interaction: discord.Interaction, name: str):
        # PHẢI AWAIT: Kiểm tra embed tồn tại
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho `level boost` bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["lv_embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `level boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="role", description="booster role định danh")
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        config = await get_guild_config(interaction.guild.id)
        config["booster_role"] = role.id
        await save_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"đặt `booster role` thành công: {role.mention}", ephemeral=False)

    # --- CÁC LỆNH CƠ BẢN (Boost thường) ---

    @app_commands.command(name="channel", description="kênh thông báo boost")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = await get_guild_config(interaction.guild.id)
        config["channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"đặt kênh `boost` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="nội dung thông báo boost")
    async def message(self, interaction: discord.Interaction, text: str):
        config = await get_guild_config(interaction.guild.id)
        config["message"] = text
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung `boost` thành công: `{text}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed cho boost")
    async def embed(self, interaction: discord.Interaction, name: str):
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho `boost` bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    # --- TEST TOOLS ---

    @app_commands.command(name="lv_test", description="giả lập ngày boost")
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=False)
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)
        try:
            await assign_correct_level(interaction.user, mock_days=days)
            await interaction.followup.send(f"giả lập `{days} ngày` thành công (bypass 5 phút)", ephemeral=False)
        except Exception as e:
            await interaction.followup.send(f"phát sinh lỗi: `{e}`", ephemeral=False)

    @app_commands.command(name="test", description="test hệ thống boost")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)
        
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        
        if success:
            embed = discord.Embed(
                description=f"{Emojis.MATTRANG} kiểm tra hệ thống `boost` thành công",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} kiểm tra thất bại, hãy xem lại cấu hình kênh hoặc embed của hệ thống `boost` nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER & RADAR
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [VÁ LỖI] Quản lý tác vụ để giải phóng RAM Member kịp thời
        self._tasks = set()
        self.booster_radar.start()

    def cog_unload(self):
        """[VÁ LỖI] Dọn dẹp tuyệt đối các tác vụ ngầm khi reload module"""
        self.booster_radar.cancel()
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot: return
        if (before.premium_since is None and after.premium_since is not None) or \
           (before.premium_since is not None and after.premium_since is None):
            
            send_welcome = (before.premium_since is None and after.premium_since is not None)
            if send_welcome:
                task_welcome = asyncio.create_task(send_config_message(after.guild, after, "booster"))
                self._tasks.add(task_welcome)
                task_welcome.add_done_callback(self._tasks.discard)
            
            task_sync = asyncio.create_task(assign_correct_level(after))
            self._tasks.add(task_sync)
            task_sync.add_done_callback(self._tasks.discard)

    @tasks.loop(minutes=5)
    async def booster_radar(self):
        await self.bot.wait_until_ready()
        now = time.time()
        # [VÁ LỖI] Lấy UI Data một lần duy nhất mỗi chu kỳ quét
        ui_data = await State.get_ui("test_bypass") or {}
        
        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            rid = config.get("booster_role")
            if not rid: continue
            role = guild.get_role(int(rid))
            if not role: continue

            # [VÁ LỖI] Xử lý có kiểm soát tốc độ để tránh làm bot bị nghẽn (Throttle)
            for booster in guild.premium_subscribers:
                task = asyncio.create_task(assign_correct_level(booster))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
                await asyncio.sleep(0.1)

            for member in role.members:
                if member.premium_since is None and str(member.id) not in ui_data:
                    task = asyncio.create_task(assign_correct_level(member, mock_days=0))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
                    await asyncio.sleep(0.1)

            # Dọn dẹp bypass data
            cleanup_needed = False
            for uid_s, expiry in list(ui_data.items()):
                if now > expiry: 
                    ui_data.pop(uid_s)
                    cleanup_needed = True
            
            if cleanup_needed:
                await State.set_ui("test_bypass", ui_data)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "boost" for c in p_cmd.commands):
            p_cmd.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
    print("[load] success: core.booster", flush=True)
