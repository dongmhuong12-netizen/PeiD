import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict

from core.greet_storage import get_section, update_guild_config
from core.booster_storage import get_guild_config as get_booster_cfg # [FIX 1] Nạp kho Booster
from core.embed_storage import load_embed
from core.variable_engine import apply_variables
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# [VÁ LỖI] Lock theo Guild để bảo vệ trí nhớ cấu hình khi admin setup song song
_config_locks = defaultdict(asyncio.Lock)

# ======================
# AUTOCOMPLETE HELPER (SAFE)
# ======================

async def _embed_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        # Giả định lớp storage của cậu có hàm list_embeds hoặc tương đương để lấy danh sách tên embed
        from core.embed_storage import list_embeds
        embed_list = await list_embeds(interaction.guild_id)
        return [
            app_commands.Choice(name=name, value=name)
            for name in embed_list if current.lower() in name.lower()
        ][:25]
    except Exception:
        # Trả về danh sách trống nếu chưa có hàm bổ trợ bên storage để tránh crash hệ thống
        return []

# ======================
# SEND MESSAGE HANDLER (ATOMIC)
# ======================

async def send_config_message(guild: discord.Guild, member: discord.Member, section: str):
    """
    xử lý gửi tin nhắn greet/leave/booster tập trung.
    """
    # 1. nạp cấu hình từ bộ nhớ - [SỬA LỖI] Phân luồng kho dữ liệu để fix lỗi test boost
    if section == "booster":
        config = await get_booster_cfg(guild.id)
    else:
        config = await get_section(guild.id, section)
    
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] 
    # Logic nạp thủ công từ "booster_levels" qua cache_manager đã bị gỡ bỏ.
    # Cậu hãy xử lý việc hợp nhất (merge) dữ liệu này ngay trong lớp Storage (greet_storage) 
    # khi nạp từ MongoDB để file Engine này hoàn toàn Stateless.

    if not config: return False

    # [GIA CỐ] Hỗ trợ đọc cả key mới (channel_id/embed_name) và key cũ (legacy) để Dashboard ko bị none
    channel_id = config.get("channel_id") or config.get("channel") or config.get("booster_channel")
    message_text = config.get("message") or config.get("booster_message")
    embed_name = config.get("embed_name") or config.get("embed") or config.get("booster_embed")

    if not channel_id: return False

    channel = guild.get_channel(int(channel_id))
    if not channel: return False

    perms = channel.permissions_for(guild.me)
    if not perms.send_messages: return False

    try:
        final_content = None
        final_embed = None

        if message_text:
            final_content = apply_variables(message_text, guild, member)

        if embed_name and perms.embed_links:
            embed_data = await load_embed(guild.id, embed_name)
            if embed_data:
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        # Trả về True nếu có ít nhất text hoặc embed để gửi
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False
    except Exception as e:
        print(f"[greet/leave error] {section} fail in {guild.id}: {e}", flush=True)
        return False

# ======================
# COMMAND GROUPS
# ======================

class GreetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="greet", description="cấu hình hệ thống chào mừng")

    @app_commands.command(name="channel", description="đặt kênh gửi tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # [GIA CỐ] Defer sớm chống lỗi 10062
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # Chuẩn hóa key lưu DB
            await update_guild_config(gid, "greet", "channel_id", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} đặt kênh `greet` thành công: {channel.mention}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_guild_config(gid, "greet", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        display_msg = apply_variables(message, interaction.guild, interaction.user)
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật tin nhắn `greet` thành công: {display_msg}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="gán embed cho hệ thống greet")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy thử lại lần nữa nhé. **yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho greet bằng `/p embed edit`",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # Chuẩn hóa key lưu DB
            await update_guild_config(gid, "greet", "embed_name", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật embed `{name}` cho hệ thống `greet` thành công",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @embed.autocomplete('name')
    async def embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    @app_commands.command(name="test", description="gửi thử tin nhắn chào mừng")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_config_message(interaction.guild, interaction.user, "greet")
        
        if success:
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} test `greet` thành công",
                description="hãy kiểm tra tại kênh được setup nhé. nếu không thấy embed, hãy kiểm tra lại quyền của **yiyi** hoặc quyền của kênh",
                color=0xe6e2dd
            )
        else:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed",
                description="hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xe6e2dd
            )
        await interaction.followup.send(embed=embed)

class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="cấu hình hệ thống tạm biệt")

    @app_commands.command(name="channel", description="đặt kênh gửi tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_guild_config(gid, "leave", "channel_id", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} đặt kênh `leave` thành công: {channel.mention}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_guild_config(gid, "leave", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        display_msg = apply_variables(message, interaction.guild, interaction.user)
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật tin nhắn `leave` thành công: {display_msg}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="gán embed cho hệ thống leave")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy thử lại lần nữa nhé. **yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho leave bằng `/p embed edit`",
                color=0xe6e2dd
            )
            # [FIX TYPO] Đã sửa biến err thành embed_err
            return await interaction.followup.send(embed=embed_err)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_guild_config(gid, "leave", "embed_name", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật embed `{name}` cho hệ thống `leave` thành công",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @embed.autocomplete('name')
    async def embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    @app_commands.command(name="test", description="gửi thử tin nhắn tạm biệt")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_config_message(interaction.guild, interaction.user, "leave")
        
        if success:
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} test `leave` thành công",
                description="hãy kiểm tra tại kênh được setup nhé. nếu không thấy embed, hãy kiểm tra lại quyền của **yiyi** hoặc quyền của kênh",
                color=0xe6e2dd
            )
        else:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed",
                description="hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xe6e2dd
            )
        await interaction.followup.send(embed=embed)

# ======================
# LISTENER & SETUP
# ======================

class GreetLeaveListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [VÁ LỖI] Hệ thống quản lý tác vụ ngầm
        self._tasks = set()

    def cog_unload(self):
        """[VÁ LỖI] Dọn dẹp tuyệt đối các tác vụ đang chạy khi reload module"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # [VÁ LỖI] Đăng ký tác vụ vào bộ quản lý
        task = asyncio.create_task(send_config_message(member.guild, member, "greet"))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # [VÁ LỖI] Đăng ký tác vụ vào bộ quản lý
        task = asyncio.create_task(send_config_message(member.guild, member, "leave"))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "greet" for c in p_cmd.commands):
            p_cmd.add_command(GreetGroup())
        if not any(c.name == "leave" for c in p_cmd.commands):
            p_cmd.add_command(LeaveGroup())
    
    await bot.add_cog(GreetLeaveListener(bot))
    print("[load] success: core.greet_leave (Industrial Fix Applied)", flush=True)
