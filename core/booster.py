import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Kết nối hệ thống Cache và Storage mới
from core.cache_manager import get_raw, mark_dirty
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels, get_guild_config
from core.booster_level_ui import BoosterLevelView

FILE_KEY = "booster_levels"
_test_bypass = {} # Lưu trữ ID người đang test: {user_id: expiry_timestamp}

# ======================
# BOOST GROUP
# ======================

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="boost",
            description="Hệ thống xử lý khi thành viên Boost server"
        )
        self.active_editors = {}

    @app_commands.command(name="lv_create", description="Mở bảng chỉnh Booster Level")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_create(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        config = await get_guild_config(guild.id)
        booster_role = config.get("booster_role")

        if not booster_role:
            return await interaction.followup.send(
                "Server chưa thiết lập booster role trước bằng `/boost role`.",
                ephemeral=True
            )

        old_view = self.active_editors.get(guild.id)
        if old_view:
            try:
                old_view.stop()
            except: pass

        levels = await get_levels(guild.id) or [{
            "role": booster_role,
            "days": 0
        }]

        view = BoosterLevelView(
            guild_id=guild.id,
            booster_role=booster_role,
            levels=[lvl.copy() for lvl in levels]
        )

        embed = view.build_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        try:
            msg = await interaction.original_response()
            view.message = msg
            self.active_editors[guild.id] = view
        except: pass

    @app_commands.command(name="lv_channel", description="Đặt kênh thông báo level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = get_raw(FILE_KEY)
        gid = str(interaction.guild.id)
        if gid not in db: db[gid] = {}
        
        db[gid]["channel"] = str(channel.id)
        mark_dirty(FILE_KEY)
        await interaction.response.send_message(f"✅ Đặt kênh level boost thành công: {channel.mention}", ephemeral=True)

    @app_commands.command(name="lv_test", description="Test booster level theo số ngày")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        # Cấp giấy thông hành test
        _test_bypass[interaction.user.id] = time.time() + 300

        try:
            await assign_correct_level(interaction.user)
        except: pass

        await interaction.followup.send(f"✅ Đã test booster level với {days} ngày (Giữ role 5p).", ephemeral=True)

    @app_commands.command(name="channel", description="Đặt kênh gửi thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = get_raw(FILE_KEY)
        gid = str(interaction.guild.id)
        if gid not in db: db[gid] = {}
        
        db[gid]["booster_channel"] = str(channel.id)
        mark_dirty(FILE_KEY)
        await interaction.response.send_message(f"✅ Đặt kênh Boost thành công: {channel.mention}", ephemeral=True)

    @app_commands.command(name="role", description="Đặt role sẽ được gán cho người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        db = get_raw(FILE_KEY)
        gid = str(interaction.guild.id)
        if gid not in db: db[gid] = {}
        
        db[gid]["booster_role"] = str(role.id)
        mark_dirty(FILE_KEY)
        await interaction.response.send_message(f"✅ Đặt role Boost thành công: {role.mention}", ephemeral=True)

    @app_commands.command(name="test", description="Kiểm tra hệ thống booster")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Cấp giấy thông hành 5 phút
        _test_bypass[interaction.user.id] = time.time() + 300

        member = interaction.user
        guild = interaction.guild
        config = await get_guild_config(guild.id)
        role_id = config.get("booster_role")
        role = guild.get_role(int(role_id)) if role_id else None

        if role and role.position < guild.me.top_role.position:
            try:
                await member.add_roles(role, reason="Booster Test Bypass")
            except: pass

        success = await send_config_message(guild, member, "booster")
        msg = "✅ Test Boost thành công. Role được giữ trong 5p." if success else "⚠️ Thiếu cấu hình booster."
        await interaction.followup.send(msg, ephemeral=True)


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
        
        # Nếu đang trong thời gian bypass, không can thiệp role
        if after.id in _test_bypass and time.time() < _test_bypass[after.id]:
            return

        # Logic Cưỡng ép đồng bộ: Có boost là gán, không là gỡ
        is_boosting = after.premium_since is not None
        await self.sync_booster_status(after, is_boosting)

    async def sync_booster_status(self, member: discord.Member, is_active: bool):
        guild = member.guild
        config = await get_guild_config(guild.id)
        role_id = config.get("booster_role")
        role = guild.get_role(int(role_id)) if role_id else None

        if not role or not guild.me or role.position >= guild.me.top_role.position:
            return

        try:
            if is_active:
                if role not in member.roles:
                    await member.add_roles(role, reason="Sync: Boost detected")
                    await send_config_message(guild, member, "booster")
            else:
                # Chỉ gỡ nếu không trong diện bypass test
                if role in member.roles and member.id not in _test_bypass:
                    await member.remove_roles(role, reason="Sync: Boost ended")
        except: pass

        # Bao bọc hệ Level dở dang
        try:
            await assign_correct_level(member)
        except: pass

    @tasks.loop(minutes=10)
    async def booster_radar(self):
        """Radar quét định kỳ dọn role rác (10 phút/lần)"""
        await self.bot.wait_until_ready()
        now = time.time()

        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            role_id = config.get("booster_role")
            role = guild.get_role(int(role_id)) if role_id else None
            if not role: continue

            for member in role.members:
                if member.bot: continue
                
                # Check giấy thông hành test
                if member.id in _test_bypass:
                    if now < _test_bypass[member.id]: continue
                    else: _test_bypass.pop(member.id)

                if member.premium_since is None:
                    try:
                        await member.remove_roles(role, reason="Radar: Boost not found")
                    except: pass
                await asyncio.sleep(0.1)

    @commands.Cog.listener()
    async def on_ready(self):
        print("🚀 Booster System: Radar & Sync Active")

async def setup(bot):
    # Đăng ký Group Command
    if not any(isinstance(c, BoostGroup) for c in bot.tree.get_commands()):
        bot.tree.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
