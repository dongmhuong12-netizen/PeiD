import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels, get_guild_config
from core.booster_level_ui import BoosterLevelView

FILE_KEY = "booster_levels"
_test_bypass = {} # {user_id: timestamp_hết_hạn}


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
                "Server chưa thiết lập booster role trước.",
                ephemeral=True
            )

        old_view = self.active_editors.get(guild.id)
        if old_view:
            try:
                if old_view.message:
                    await old_view.message.edit(view=None)
            except Exception:
                pass
            old_view.stop()

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

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

        try:
            msg = await interaction.original_response()
            view.message = msg
            self.active_editors[guild.id] = view
        except Exception:
            pass

    @app_commands.command(name="lv_channel", description="Đặt kênh thông báo level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_channel(self, interaction: discord.Interaction, channel_id: str):
        if not channel_id.isdigit():
            return await interaction.response.send_message(
                "ID kênh không hợp lệ.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Không tìm thấy text channel.",
                ephemeral=True
            )

        update_guild_config(
            interaction.guild.id,
            "booster_level",
            "channel",
            channel.id
        )

        await interaction.response.send_message(
            f"Đặt kênh level boost thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="lv_message", description="Đặt nội dung level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(
            interaction.guild.id,
            "booster_level",
            "message",
            text
        )

        await interaction.response.send_message(
            "Đặt message booster level thành công.",
            ephemeral=True
        )

    @app_commands.command(name="lv_embed", description="Gán embed cho level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )

        update_guild_config(
            interaction.guild.id,
            "booster_level",
            "embed",
            name
        )

        await interaction.response.send_message(
            f"Đặt embed level boost thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="lv_test", description="Test booster level theo số ngày")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        _test_bypass[interaction.user.id] = time.time() + 300

        try:
            await assign_correct_level(interaction.user)
        except Exception:
            pass

        await interaction.followup.send(
            f"Đã test booster level với {days} ngày (Giữ role 5p).",
            ephemeral=True
        )

    @app_commands.command(name="channel", description="Đặt kênh gửi thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_id: str):
        if not channel_id.isdigit():
            return await interaction.response.send_message(
                "ID kênh không hợp lệ.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Không tìm thấy text channel.",
                ephemeral=True
            )

        update_guild_config(
            interaction.guild.id,
            "booster",
            "channel",
            channel.id
        )

        await interaction.response.send_message(
            f"Đặt kênh Boost thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):
        update_guild_config(
            interaction.guild.id,
            "booster",
            "message",
            text
        )

        await interaction.response.send_message(
            f"Đặt nội dung Boost thành công: {text}",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Gán embed đã tạo cho thông báo booster")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )

        update_guild_config(
            interaction.guild.id,
            "booster",
            "embed",
            name
        )

        await interaction.response.send_message(
            f"Đặt embed Boost thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="role", description="Đặt role sẽ được gán cho người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role_input: str):
        guild = interaction.guild

        role_id = (
            role_input.replace("<@&", "").replace(">", "")
            if role_input.startswith("<@&")
            else role_input
        )

        if not role_id.isdigit():
            return await interaction.response.send_message(
                "ID Role không hợp lệ.",
                ephemeral=True
            )

        role = guild.get_role(int(role_id))
        if not role:
            return await interaction.response.send_message(
                "Role không tồn tại.",
                ephemeral=True
            )

        # Sync sang cache manager
        from core.cache_manager import get_raw, mark_dirty
        db = get_raw(FILE_KEY)
        gid = str(guild.id)
        if gid not in db: db[gid] = {}
        db[gid]["booster_role"] = int(role_id)
        mark_dirty(FILE_KEY)

        update_guild_config(guild.id, "booster", "role", role.id)

        await interaction.response.send_message(
            f"Đặt role Boost thành công: {role.mention}",
            ephemeral=True
        )

    @app_commands.command(name="test", description="Kiểm tra hệ thống booster")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        _test_bypass[interaction.user.id] = time.time() + 300
        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        config = await get_guild_config(guild.id)
        role_id = config.get("booster_role")
        role = guild.get_role(int(role_id)) if role_id else None

        if role and role.position < bot_member.top_role.position:
            try:
                await member.add_roles(role, reason="Booster Test Bypass")
            except Exception:
                pass

        # Lệnh TEST thì vẫn gửi message để Admin kiểm tra nội dung
        success = await send_config_message(guild, member, "booster")
        msg = "Test Boost thành công (Giữ role 5p)." if success else "Thiếu cấu hình booster."

        await interaction.followup.send(msg, ephemeral=True)


# ======================
# LISTENER
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.booster_radar.start()

    def cog_unload(self):
        self.booster_radar.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return

        if after.id in _test_bypass and time.time() < _test_bypass[after.id]:
            return

        # Chỉ gửi Embed khi có sự kiện NGƯỜI DÙNG MỚI nhấn nút Boost
        if not before.premium_since and after.premium_since:
            await self.handle_boost_sync(after, True, send_embed=True)
        # Các trường hợp thay đổi khác (ví dụ admin gỡ role tay) hoặc hết hạn boost
        else:
            is_active = after.premium_since is not None
            await self.handle_boost_sync(after, is_active, send_embed=False)

    async def handle_boost_sync(self, member: discord.Member, boosted: bool, send_embed: bool = False):
        guild = member.guild
        config = await get_guild_config(guild.id)
        role_id = config.get("booster_role")
        role = guild.get_role(int(role_id)) if role_id else None

        if not role or not guild.me or role.position >= guild.me.top_role.position:
            return

        try:
            if boosted:
                if role not in member.roles:
                    await member.add_roles(role, reason="Server Boost Sync")
                    if send_embed:
                        await send_config_message(guild, member, "booster")
            else:
                if role in member.roles and member.id not in _test_bypass:
                    await member.remove_roles(role, reason="Boost Ended")
        except discord.Forbidden:
            return

        try:
            await assign_correct_level(member)
        except Exception:
            pass

    @tasks.loop(minutes=5)
    async def booster_radar(self):
        """Radar quét dọn và đồng bộ im lặng (Không gửi Embed chúc mừng)"""
        await self.bot.wait_until_ready()
        now = time.time()

        for guild in self.bot.guilds:
            config = await get_guild_config(guild.id)
            role_id = config.get("booster_role")
            role = guild.get_role(int(role_id)) if role_id else None
            if not role: continue

            # Gán im lặng cho người boost thật (Dùng handle_boost_sync với send_embed=False)
            for booster in guild.premium_subscribers:
                if role not in booster.roles:
                    await self.handle_boost_sync(booster, True, send_embed=False)
                await asyncio.sleep(0.1)

            # Gỡ im lặng người giả hoặc hết hạn test
            for member in role.members:
                if member.bot: continue
                if member.id in _test_bypass:
                    if now < _test_bypass[member.id]: continue
                    else: _test_bypass.pop(member.id)

                if member.premium_since is None:
                    try:
                        await member.remove_roles(role, reason="Radar: Silent Clean Up")
                    except: pass
                await asyncio.sleep(0.1)

    @commands.Cog.listener()
    async def on_ready(self):
        print("🚀 Booster System: Radar & Sync READY")


async def setup(bot):
    if not any(isinstance(c, BoostGroup) for c in bot.tree.get_commands()):
        bot.tree.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
