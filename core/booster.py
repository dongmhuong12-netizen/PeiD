import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Imports hệ thống
from core.cache_manager import get_raw, mark_dirty
from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels, get_guild_config
from core.booster_level_ui import BoosterLevelView

FILE_KEY = "booster_levels"
_test_bypass = {} # Lưu trữ ID người đang test không giới hạn: {user_id: timestamp_hết_hạn}

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="boost", description="Hệ thống xử lý Booster")
        self.active_editors = {}

    # --- SETUP COMMANDS (Giữ nguyên 100% logic của Nguyệt) ---

    @app_commands.command(name="lv_create", description="Mở bảng chỉnh Booster Level")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_create(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = await get_guild_config(interaction.guild.id)
        booster_role = config.get("booster_role")
        if not booster_role:
            return await interaction.followup.send("❌ Cần đặt booster role trước.", ephemeral=True)
        old_view = self.active_editors.get(interaction.guild.id)
        if old_view:
            try: old_view.stop()
            except: pass
        levels = await get_levels(interaction.guild.id) or [{"role": booster_role, "days": 0}]
        view = BoosterLevelView(guild_id=interaction.guild.id, booster_role=booster_role, levels=[lvl.copy() for lvl in levels])
        await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)
        try:
            msg = await interaction.original_response()
            view.message = msg
            self.active_editors[interaction.guild.id] = view
        except: pass

    @app_commands.command(name="role", description="Đặt role gán cho người boost")
    async def role(self, interaction: discord.Interaction, role_input: str):
        role_id = role_input.replace("<@&", "").replace(">", "")
        if not role_id.isdigit(): return await interaction.response.send_message("ID lỗi.", ephemeral=True)
        db = get_raw(FILE_KEY); gid = str(interaction.guild.id)
        if gid not in db: db[gid] = {}
        db[gid]["booster_role"] = int(role_id)
        mark_dirty(FILE_KEY)
        update_guild_config(interaction.guild.id, "booster", "role", int(role_id))
        await interaction.response.send_message(f"✅ Đã cập nhật role booster.", ephemeral=True)

    @app_commands.command(name="test", description="Lệnh test booster (Giữ role 5p)")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Cấp "giấy thông hành" cho ID người gọi lệnh (không giới hạn số người test)
        _test_bypass[interaction.user.id] = time.time() + 300
        config = await get_guild_config(interaction.guild.id)
        role_id = config.get("booster_role")
        role = interaction.guild.get_role(int(role_id)) if role_id else None
        if role:
            try: await interaction.user.add_roles(role, reason="Manual Test Bypass")
            except: pass
        await send_config_message(interaction.guild, interaction.user, "booster")
        await interaction.followup.send("✅ Đã gán role test. Radar sẽ check và gỡ sau 5 phút nếu không boost thật.", ephemeral=True)

    # --- KHÔI PHỤC CÁC LỆNH SETUP KHÁC ---
    @app_commands.command(name="channel")
    async def channel(self, interaction: discord.Interaction, channel_id: str):
        update_guild_config(interaction.guild.id, "booster", "channel", int(channel_id))
        await interaction.response.send_message("✅ Đã đặt kênh.", ephemeral=True)

    @app_commands.command(name="message")
    async def message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "booster", "message", text)
        await interaction.response.send_message("✅ Đã đặt message.", ephemeral=True)

    @app_commands.command(name="embed")
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster", "embed", name)
        await interaction.response.send_message(f"✅ Đã đặt embed.", ephemeral=True)

# ======================
# LISTENER & RADAR (VÙNG CƯỠNG ÉP LOGIC)
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
        # Nếu đang trong thời gian bypass test, Listener không được gỡ role
        if after.id in _test_bypass and time.time() < _test_bypass[after.id]:
            return
        is_active = after.premium_since is not None
        await self.sync_member_role(after, is_active)

    async def sync_member_role(self, member: discord.Member, is_active: bool):
        config = await get_guild_config(member.guild.id)
        role_id = config.get("booster_role")
        role = member.guild.get_role(int(role_id)) if role_id else None
        if not role or not member.guild.me or role.position >= member.guild.me.top_role.position:
            return

        try:
            if is_active:
                if role not in member.roles:
                    await member.add_roles(role, reason="Sync: Phát hiện Boost thật")
                    await send_config_message(member.guild, member, "booster")
            else:
                if role in member.roles and member.id not in _test_bypass:
                    await member.remove_roles(role, reason="Sync: Không có Boost")
        except: pass
        try: await assign_correct_level(member)
        except: pass

    @tasks.loop(minutes=5)
    async def booster_radar(self):
        """Radar quét 2 chiều: Cưỡng ép gán cho người boost thật & Cưỡng ép gỡ người giả"""
        await self.bot.wait_until_ready()
        now = time.time()

        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            role_id = config.get("booster_role")
            role = guild.get_role(int(role_id)) if role_id else None
            if not role: continue

            # CHIỀU 1: QUÉT TẤT CẢ NGƯỜI BOOST THẬT (Gán role nếu thiếu)
            for booster in guild.premium_subscribers:
                if role not in booster.roles:
                    try:
                        await booster.add_roles(role, reason="Radar: Cưỡng ép gán role người boost thật")
                        await send_config_message(guild, booster, "booster")
                    except: pass
                await asyncio.sleep(0.1)

            # CHIỀU 2: QUÉT NHỮNG NGƯỜI ĐANG GIỮ ROLE (Dọn rác)
            for member in role.members:
                if member.bot: continue
                # Xử lý Logic Bypass
                if member.id in _test_bypass:
                    if now < _test_bypass[member.id]:
                        continue # Còn hạn 5p -> Tha
                    else:
                        _test_bypass.pop(member.id) # Hết hạn -> Xóa tên để check gỡ ở dưới

                # Nếu cầm role mà KHÔNG boost thật -> GỠ NGAY
                if member.premium_since is None:
                    try: await member.remove_roles(role, reason="Radar: Boost giả/Hết hạn")
                    except: pass
                await asyncio.sleep(0.1)

async def setup(bot):
    if not any(isinstance(c, BoostGroup) for c in bot.tree.get_commands()):
        bot.tree.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
