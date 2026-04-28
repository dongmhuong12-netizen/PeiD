import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Import các công cụ quản lý bộ nhớ
from core.cache_manager import get_raw, mark_dirty, save
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels, get_guild_config
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
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_channel"] = channel.id
        mark_dirty(FILE_KEY)
        # ÉP LƯU: Để không bị mất dữ liệu
        await save(FILE_KEY)
        await interaction.response.send_message(f"đặt kênh `level boost` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="lv_message", description="đặt nội dung thông báo level boost")
    async def lv_message(self, interaction: discord.Interaction, text: str):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_message"] = text
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        
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
        
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_embed"] = name
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `level boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="role", description="booster role định danh")
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        db = get_raw(FILE_KEY)
        # Đồng bộ hóa bộ nhớ booster
        db.setdefault(str(interaction.guild.id), {})["booster_role"] = role.id
        mark_dirty(FILE_KEY)
        # QUAN TRỌNG: Ép lưu booster role ngay lập tức
        await save(FILE_KEY)
        await interaction.response.send_message(f"đặt `booster role` thành công: {role.mention}", ephemeral=False)

    # --- CÁC LỆNH CƠ BẢN (Boost thường) ---

    @app_commands.command(name="channel", description="kênh thông báo boost")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["channel"] = channel.id
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message(f"đặt kênh `boost` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="nội dung thông báo boost")
    async def message(self, interaction: discord.Interaction, text: str):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["message"] = text
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        
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
        
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["embed"] = name
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        
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
        self.booster_radar.start()

    def cog_unload(self):
        self.booster_radar.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot: return
        if (before.premium_since is None and after.premium_since is not None) or \
           (before.premium_since is not None and after.premium_since is None):
            
            send_welcome = (before.premium_since is None and after.premium_since is not None)
            if send_welcome:
                asyncio.create_task(send_config_message(after.guild, after, "booster"))
            
            asyncio.create_task(assign_correct_level(after))

    @tasks.loop(minutes=5)
    async def booster_radar(self):
        await self.bot.wait_until_ready()
        now = time.time()
        ui_data = await State.get_ui("test_bypass") or {}
        
        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            rid = config.get("booster_role")
            if not rid: continue
            role = guild.get_role(int(rid))
            if not role: continue

            for booster in guild.premium_subscribers:
                asyncio.create_task(assign_correct_level(booster))
                await asyncio.sleep(0.05)

            for member in role.members:
                if member.premium_since is None and str(member.id) not in ui_data:
                    asyncio.create_task(assign_correct_level(member, mock_days=0))
                    await asyncio.sleep(0.05)

            for uid_s, expiry in list(ui_data.items()):
                if now > expiry: 
                    ui_data.pop(uid_s)
                    await State.set_ui("test_bypass", ui_data)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "boost" for c in p_cmd.commands):
            p_cmd.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
    print("[load] success: core.booster", flush=True)
