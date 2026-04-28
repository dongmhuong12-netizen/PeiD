import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.variable_engine import apply_variables
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

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
        update_guild_config(interaction.guild.id, "wellcome", "channel", channel.id)
        await interaction.response.send_message(f"đặt kênh `wellcome` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "wellcome", "message", message)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung wellcome thành công: `{message}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed cho hệ thống wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        # FIX: PHẢI AWAIT load_embed
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho wellcome bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        update_guild_config(interaction.guild.id, "wellcome", "embed", name)
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `wellcome` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn wellcome")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_wellcome(interaction.guild, interaction.user)
        
        if success:
            embed = discord.Embed(
                description=f"{Emojis.MATTRANG} test `wellcome` thành công, hãy kiểm tra tại kênh được setup nhé. nếu không thấy, hãy kiểm tra lại quyền của bot hoặc quyền của kênh",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed. hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER & INJECTION
# ======================

class WellcomeListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        asyncio.create_task(send_wellcome(member.guild, member))

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "wellcome" for c in p_cmd.commands):
            p_cmd.add_command(WellcomeGroup())
    
    await bot.add_cog(WellcomeListener(bot))
    print("[load] success: core.wellcome (injected into /p)", flush=True)
