import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Import các công cụ quản lý bộ nhớ
from core.cache_manager import get_raw, mark_dirty, save # Thêm save để ép lưu
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels, get_guild_config
from core.state import State 

FILE_KEY = "booster_levels"

# ======================
# BOOST GROUP (Logic chính)
# ======================

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="boost", description="Hệ thống quản lý Server Boost")
        self.active_editors = {}

    @app_commands.command(name="lv_create", description="Mở bảng thiết kế Booster Level")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_create(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        
        # PHẢI AWAIT: Lấy cấu hình đã lưu
        config = await get_guild_config(guild.id)
        booster_role_id = config.get("booster_role")

        if not booster_role_id:
            return await interaction.followup.send("❌ Hãy thiết lập Booster Role trước bằng `/p boost role`.", ephemeral=True)

        from core.booster_level_ui import BoosterLevelView
        levels = await get_levels(guild.id) or [{"role": str(booster_role_id), "days": 0}]
        
        view = BoosterLevelView(guild_id=guild.id, booster_role=booster_role_id, levels=levels)
        view.timeout = 600 
        embed = view.build_embed()
        
        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg
        self.active_editors[guild.id] = view

    @app_commands.command(name="lv_channel", description="Đặt kênh thông báo Level Boost")
    async def lv_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_channel"] = channel.id
        mark_dirty(FILE_KEY)
        # ÉP LƯU: Để không bị mất khi Render restart
        await save(FILE_KEY)
        await interaction.response.send_message(f"✅ Đã đặt kênh Level Boost: {channel.mention}", ephemeral=True)

    @app_commands.command(name="lv_message", description="Đặt nội dung thông báo Level Boost")
    async def lv_message(self, interaction: discord.Interaction, text: str):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_message"] = text
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message("✅ Đã cập nhật tin nhắn Level Boost.", ephemeral=True)

    @app_commands.command(name="lv_embed", description="Gán Embed cho Level Boost")
    async def lv_embed(self, interaction: discord.Interaction, name: str):
        # PHẢI AWAIT: Kiểm tra embed tồn tại
        if not await load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["lv_embed"] = name
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Level Boost.", ephemeral=True)

    @app_commands.command(name="role", description="Booster Role định danh")
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        db = get_raw(FILE_KEY)
        # Đồng bộ hóa bộ nhớ Booster
        db.setdefault(str(interaction.guild.id), {})["booster_role"] = role.id
        mark_dirty(FILE_KEY)
        
        # QUAN TRỌNG: Ép lưu Booster Role ngay lập tức
        await save(FILE_KEY)
        
        await interaction.response.send_message(f"✅ Đã đặt Booster Role: {role.mention}", ephemeral=True)

    # --- CÁC LỆNH CƠ BẢN (Boost thường) ---

    @app_commands.command(name="channel", description="Kênh thông báo Boost")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["channel"] = channel.id
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message(f"✅ Đã đặt kênh Boost: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Nội dung thông báo Boost")
    async def message(self, interaction: discord.Interaction, text: str):
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["message"] = text
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message("✅ Đã cập nhật tin nhắn Boost.", ephemeral=True)

    @app_commands.command(name="embed", description="Gán Embed cho Boost")
    async def embed(self, interaction: discord.Interaction, name: str):
        if not await load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["embed"] = name
        mark_dirty(FILE_KEY)
        await save(FILE_KEY)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Boost.", ephemeral=True)

    # --- TEST TOOLS ---

    @app_commands.command(name="lv_test", description="Giả lập ngày Boost")
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)
        try:
            await assign_correct_level(interaction.user, mock_days=days)
            await interaction.followup.send(f"✅ Giả lập **{days} ngày** thành công (Bypass 5p).", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

    @app_commands.command(name="test", description="Test hệ thống Boost")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)
        await send_config_message(interaction.guild, interaction.user, "booster")
        await interaction.followup.send("✅ Test Boost hoàn tất!", ephemeral=True)

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
