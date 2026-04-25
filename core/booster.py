import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

from core.greet_storage import update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level # Sẽ check ở file sau
from core.booster_storage import get_levels, get_guild_config
from core.state import State 

FILE_KEY = "booster_levels"

# ======================
# BOOST GROUP (MEAT)
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

    # --- KHÔI PHỤC NHÓM LỆNH CẤU HÌNH LEVEL (CỦA NGUYỆT) ---

    @app_commands.command(name="lv_channel", description="Đặt kênh thông báo khi thành viên lên cấp Boost")
    async def lv_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "booster_level", "channel", channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh thông báo Level Boost: {channel.mention}", ephemeral=True)

    @app_commands.command(name="lv_message", description="Đặt nội dung thông báo khi lên cấp Boost")
    async def lv_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "booster_level", "message", text)
        await interaction.response.send_message("✅ Đã cập nhật tin nhắn Level Boost.", ephemeral=True)

    @app_commands.command(name="lv_embed", description="Gán Embed cho thông báo lên cấp Boost")
    async def lv_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster_level", "embed", name)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Level Boost.", ephemeral=True)

    @app_commands.command(name="lv_test", description="Giả lập số ngày Boost để kiểm tra gán Role")
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        # Lưu vào não bộ bền vững để Radar không quét dọn mất
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)

        try:
            await assign_correct_level(interaction.user, mock_days=days)
            await interaction.followup.send(f"✅ Đã giả lập **{days} ngày** Boost. Role cấp tương ứng đã được gán (Bypass 5p).", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi Engine: {e}", ephemeral=True)

    # --- NHÓM LỆNH CẤU HÌNH BOOST CƠ BẢN ---

    @app_commands.command(name="channel", description="Kênh thông báo khi có người mới Boost")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "booster", "channel", channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh thông báo Boost: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Nội dung thông báo Boost")
    async def message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "booster", "message", text)
        await interaction.response.send_message("✅ Đã cập nhật nội dung thông báo Boost.", ephemeral=True)

    @app_commands.command(name="embed", description="Gán Embed cho thông báo Boost")
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster", "embed", name)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Boost.", ephemeral=True)

    @app_commands.command(name="role", description="Role định danh cho người Boost")
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        from core.cache_manager import get_raw, mark_dirty
        db = get_raw(FILE_KEY)
        db.setdefault(str(interaction.guild.id), {})["booster_role"] = role.id
        mark_dirty(FILE_KEY)
        update_guild_config(interaction.guild.id, "booster", "role", role.id)
        await interaction.response.send_message(f"✅ Đã đặt Booster Role: {role.mention}", ephemeral=True)

    @app_commands.command(name="test", description="Kiểm tra hệ thống Boost (Basic)")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ui_data = await State.get_ui("test_bypass") or {}
        ui_data[str(interaction.user.id)] = time.time() + 300
        await State.set_ui("test_bypass", ui_data)
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        await interaction.followup.send("✅ Test Boost thành công!" if success else "❌ Thiếu cấu hình.", ephemeral=True)

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
        # Nếu có người mới Boost
        if not before.premium_since and after.premium_since:
            asyncio.create_task(self.handle_boost_sync(after, True, send_embed=True))
        # Nếu người dùng gỡ Boost
        elif before.premium_since and not after.premium_since:
            asyncio.create_task(self.handle_boost_sync(after, False))

    async def handle_boost_sync(self, member: discord.Member, is_boosted: bool, send_embed: bool = False):
        guild = member.guild
        config = await get_guild_config(guild.id)
        role_id = config.get("booster_role")
        role = guild.get_role(int(role_id)) if role_id else None
        if not role or role.position >= guild.me.top_role.position: return

        try:
            if is_boosted:
                if role not in member.roles:
                    await member.add_roles(role, reason="Server Boost Sync")
                    if send_embed: await send_config_message(guild, member, "booster")
            else:
                ui_data = await State.get_ui("test_bypass") or {}
                if role in member.roles and str(member.id) not in ui_data:
                    await member.remove_roles(role, reason="Boost Ended")
            
            await assign_correct_level(member)
        except: pass

    @tasks.loop(minutes=5)
    async def booster_radar(self):
        """Radar quét dọn chống role ảo (Tối ưu 100k+ servers)"""
        await self.bot.wait_until_ready()
        now = time.time()
        ui_data = await State.get_ui("test_bypass") or {}
        
        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            rid = config.get("booster_role")
            if not rid: continue
            role = guild.get_role(int(rid))
            if not role: continue

            # Xóa bypass test hết hạn
            for uid_s, expiry in list(ui_data.items()):
                if now > expiry: 
                    ui_data.pop(uid_s)
                    await State.set_ui("test_bypass", ui_data)

            # Quét im lặng người có role nhưng không Boost thật
            for member in role.members:
                if member.premium_since is None and str(member.id) not in ui_data:
                    try: 
                        await member.remove_roles(role, reason="Radar Sync")
                        await asyncio.sleep(0.1)
                    except: pass

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "boost" for c in p_cmd.commands):
            p_cmd.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
