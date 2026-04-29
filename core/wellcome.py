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

async def send_wellcome(guild: discord.Guild, member: discord.Member):
    """
    xử lý gửi tin nhắn wellcome phụ.
    gộp text và embed vào 1 request duy nhất để bảo vệ api discord.
    """
    config = get_section(guild.id, "wellcome")
    if not config: return False

    channel_id = config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed")

    if not channel_id: return False

    channel = guild.get_channel(int(channel_id))
    if not channel: return False

    perms = channel.permissions_for(guild.me)
    if not perms.send_messages: return False

    try:
        final_content = None
        final_embed = None

        # 1. xử lý text
        if message_text:
            final_content = apply_variables(message_text, guild, member)

        # 2. xử lý embed (đã thêm await cho load_embed)
        if embed_name and perms.embed_links:
            embed_data = await load_embed(guild.id, embed_name)
            if embed_data:
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        # 3. gửi gộp
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False
    except Exception as e:
        print(f"[wellcome error] guild {guild.id} fail: {e}", flush=True)
        return False

# ======================
# WELLCOME GROUP (MEAT)
# ======================

class WellcomeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="wellcome", description="hệ thống chào mừng phụ")

    @app_commands.command(name="channel", description="đặt kênh gửi tin nhắn wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "wellcome", "channel", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # [FIX] Dùng .name để tránh lộ mã ID thô trong Title
        # Văn phong mới: Chuyển sang Title Embed
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} đặt kênh `wellcome` thành công: {channel.name}",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "wellcome", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # [FIX] Dịch biến ngay lập tức để hiện mention tag trong phản hồi
        parsed_msg = apply_variables(message, interaction.guild, interaction.user)
        # Văn phong mới: Chuyển sang Title
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật tin nhắn `wellcome` thành công: {parsed_msg}",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed cho hệ thống wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        # FIX: PHẢI AWAIT load_embed
        if not await load_embed(interaction.guild.id, name):
            # Văn phong mới: Title & Description
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy thử lại lần nữa nhé. **yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho wellcome bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            update_guild_config(gid, "wellcome", "embed", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # Văn phong mới: Chuyển sang Title
        embed_success = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật embed `{name}` cho hệ thống `wellcome` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn wellcome")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_wellcome(interaction.guild, interaction.user)
        
        if success:
            # Văn phong mới: Title & Description
            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} test `wellcome` thành công",
                description="hãy kiểm tra tại kênh được setup nhé. nếu không thấy embed, hãy kiểm tra lại quyền của **yiyi** hoặc quyền của kênh",
                color=0xf8bbd0
            )
        else:
            # Văn phong mới: Title & Description
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed",
                description="hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER & INJECTION
# ======================

class WellcomeListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [VÁ LỖI] Quản lý tác vụ để giải phóng bộ nhớ Member/Guild kịp thời
        self._tasks = set()

    def cog_unload(self):
        """[VÁ LỖI] Hủy toàn bộ tác vụ đang chờ khi reload module"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # [VÁ LỖI] Đăng ký và tự động xóa tác vụ khi hoàn tất
        task = asyncio.create_task(send_wellcome(member.guild, member))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "wellcome" for c in p_cmd.commands):
            p_cmd.add_command(WellcomeGroup())
    
    await bot.add_cog(WellcomeListener(bot))
    print("[load] success: core.wellcome (logic fixed & persona applied)", flush=True)
