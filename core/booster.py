import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
from core.booster_storage import get_levels
from core.booster_level_ui import BoosterLevelView


# ======================
# BOOST GROUP
# ======================

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="boost", description="Hệ thống xử lý khi thành viên Boost server")

    @app_commands.command(name="lv_create", description="Mở bảng chỉnh Booster Level")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_create(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        config = get_section(guild.id, "booster") or {}
        booster_role = config.get("role")
        if not booster_role:
            return await interaction.followup.send("Server chưa thiết lập booster role trước.", ephemeral=True)

        levels = await get_levels(guild.id) or [{"role": booster_role, "days": 0}]
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
        except Exception:
            pass

    @app_commands.command(name="lv_channel", description="Đặt kênh thông báo level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_channel(self, interaction: discord.Interaction, channel_id: str):
        if not channel_id.isdigit():
            return await interaction.response.send_message("ID kênh không hợp lệ.", ephemeral=True)
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Không tìm thấy text channel.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster_level", "channel", channel.id)
        await interaction.response.send_message(f"Đặt kênh level boost thành công: {channel.mention}", ephemeral=True)

    @app_commands.command(name="lv_message", description="Đặt nội dung level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "booster_level", "message", text)
        await interaction.response.send_message("Đặt message booster level thành công.", ephemeral=True)

    @app_commands.command(name="lv_embed", description="Gán embed cho level boost")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster_level", "embed", name)
        await interaction.response.send_message(f"Đặt embed level boost thành công: `{name}`", ephemeral=True)

    @app_commands.command(name="lv_test", description="Test booster level theo số ngày")
    @app_commands.default_permissions(manage_guild=True)
    async def lv_test(self, interaction: discord.Interaction, days: int):
        await interaction.response.defer(ephemeral=True)
        try:
            await assign_correct_level(interaction.user, boost_days=days)
        except TypeError:
            await assign_correct_level(interaction.user)
        await interaction.followup.send(f"Đã test booster level với {days} ngày.", ephemeral=True)

    # ----------------------
    # BOOSTER CONFIG
    # ----------------------

    @app_commands.command(name="channel", description="Đặt kênh gửi thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_id: str):
        if not channel_id.isdigit():
            return await interaction.response.send_message("ID kênh không hợp lệ.", ephemeral=True)
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Không tìm thấy text channel.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster", "channel", channel.id)
        await interaction.response.send_message(f"Đặt kênh Boost thành công: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "booster", "message", text)
        await interaction.response.send_message(f"Đặt nội dung Boost thành công: {text}", ephemeral=True)

    @app_commands.command(name="embed", description="Gán embed đã tạo cho thông báo booster")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "booster", "embed", name)
        await interaction.response.send_message(f"Đặt embed Boost thành công: `{name}`", ephemeral=True)

    @app_commands.command(name="role", description="Đặt role sẽ được gán cho người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role_input: str):
        guild = interaction.guild
        role_id = role_input.replace("<@&", "").replace(">", "") if role_input.startswith("<@&") else role_input
        if not role_id.isdigit():
            return await interaction.response.send_message("ID Role không hợp lệ.", ephemeral=True)
        role = guild.get_role(int(role_id))
        if not role:
            return await interaction.response.send_message("Role không tồn tại.", ephemeral=True)
        update_guild_config(guild.id, "booster", "role", role.id)
        await interaction.response.send_message(f"Đặt role Boost thành công: {role.mention}", ephemeral=True)

    @app_commands.command(name="test", description="Kiểm tra hệ thống booster")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        config = get_section(guild.id, "booster") or {}
        role_id = config.get("role")
        role = guild.get_role(role_id) if role_id else None

        if role and role.position < bot_member.top_role.position:
            try:
                await member.add_roles(role, reason="Booster Test")
            except Exception as e:
                return await interaction.followup.send(f"Lỗi khi gán role: {e}", ephemeral=True)

        success = await send_config_message(guild, member, "booster")
        msg = "Test Boost thành công." if success else "Thiếu cấu hình booster."
        await interaction.followup.send(msg, ephemeral=True)


# ======================
# LISTENER
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._startup_done = False
        self.booster_sync.start()

    def cog_unload(self):
        self.booster_sync.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return
        if not before.premium_since and after.premium_since:
            await self.handle_boost(after, True)
        elif before.premium_since and not after.premium_since:
            await self.handle_boost(after, False)

    async def handle_boost(self, member: discord.Member, boosted: bool):
        guild = member.guild
        config = get_section(guild.id, "booster") or {}
        role_id = config.get("role")
        role = guild.get_role(role_id) if role_id else None

        if not role or not guild.me or role.position >= guild.me.top_role.position:
            return

        try:
            if boosted and role not in member.roles:
                await member.add_roles(role, reason="Server Boost")
            elif not boosted and role in member.roles:
                await member.remove_roles(role, reason="Boost Ended")
        except discord.Forbidden:
            return

        if boosted:
            await send_config_message(guild, member, "booster")

        try:
            await assign_correct_level(member)
        except Exception:
            pass

    @tasks.loop(minutes=30)
    async def booster_sync(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            if guild.unavailable:
                continue
            for member in guild.premium_subscribers:
                if member.bot:
                    continue
                try:
                    await assign_correct_level(member)
                except Exception:
                    pass
                await asyncio.sleep(0.2)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._startup_done:
            return
        self._startup_done = True
        for guild in self.bot.guilds:
            for member in guild.premium_subscribers:
                if member.bot:
                    continue
                try:
                    await assign_correct_level(member)
                except Exception:
                    pass
                await asyncio.sleep(0.2)


async def setup(bot):
    await bot.add_cog(BoosterListener(bot))
