import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict # [VÁ LỖI]

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.variable_engine import apply_variables
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# [VÁ LỖI] Lock theo Guild để bảo vệ trí nhớ cấu hình khi admin setup song song
_config_locks = defaultdict(asyncio.Lock)

# ======================
# SEND MESSAGE HANDLER (ATOMIC)
# ======================

async def send_config_message(guild: discord.Guild, member: discord.Member, section: str):
    """
    xử lý gửi tin nhắn greet/leave/booster tập trung.
    """
    config = get_section(guild.id, section)
    
    # [LOGIC GIỮ LẠI]: Fallback cho Booster thường (không phải level)
    if section == "booster" and (not config or not config.get("channel")):
        from core.cache_manager import get_raw
        db = get_raw("booster_levels")
        config = db.get(str(guild.id), {})

    if not config: return False

    channel_id = config.get("channel") or config.get("booster_channel")
    message_text = config.get("message") or config.get("booster_message")
    embed_name = config.get("embed") or config.get("booster_embed")

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
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "greet", "channel", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        await interaction.response.send_message(f"đặt kênh `greet` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "greet", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung greet thành công: `{message}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed cho hệ thống greet")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho greet bằng `/p embed edit`.",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "greet", "embed", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `greet` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn chào mừng")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_config_message(interaction.guild, interaction.user, "greet")
        
        if success:
            embed = discord.Embed(
                description=f"{Emojis.MATTRANG} test `greet` thành công, hãy kiểm tra tại kênh được setup nhé. nếu không thấy, hãy kiểm tra lại quyền của bot hoặc quyền của kênh",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed. hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="cấu hình hệ thống tạm biệt")

    @app_commands.command(name="channel", description="đặt kênh gửi tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "leave", "channel", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        await interaction.response.send_message(f"đặt kênh `leave` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "leave", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung leave thành công: `{message}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed cho hệ thống leave")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho leave bằng `/p embed edit`.",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "leave", "embed", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `leave` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn tạm biệt")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_config_message(interaction.guild, interaction.user, "leave")
        
        if success:
            embed = discord.Embed(
                description=f"{Emojis.MATTRANG} test `leave` thành công, hãy kiểm tra tại kênh được setup nhé. nếu không thấy, hãy kiểm tra lại quyền của bot hoặc quyền của kênh",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed. hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER & SETUP
# ======================

class GreetLeaveListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [VÁ LỖI] Hệ thống quản lý tác vụ ngầm chống Zombie Task rò rỉ RAM
        self._tasks = set()

    def cog_unload(self):
        """[VÁ LỖI] Dọn dẹp tuyệt đối các tác vụ đang chạy khi reload module"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # [VÁ LỖI] Đăng ký tác vụ vào bộ quản lý để giải phóng Member object kịp thời
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
