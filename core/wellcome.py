import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.variable_engine import apply_variables

# ======================
# SEND MESSAGE HANDLER (ATOMIC)
# ======================

async def send_wellcome(guild: discord.Guild, member: discord.Member):
    """
    Xử lý gửi tin nhắn Wellcome phụ.
    Gộp Text và Embed vào 1 request duy nhất để bảo vệ API Discord.
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

        # 1. Xử lý TEXT
        if message_text:
            final_content = apply_variables(message_text, guild, member)

        # 2. Xử lý EMBED (Đồng bộ với chuyên gia Sender)
        if embed_name and perms.embed_links:
            embed_data = load_embed(guild.id, embed_name)
            if embed_data:
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        # 3. GỬI GỘP (Single Request)
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False
    except Exception as e:
        print(f"[WELLCOME ERROR] Guild {guild.id} fail: {e}", flush=True)
        return False

# ======================
# WELLCOME GROUP (MEAT)
# ======================

class WellcomeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="wellcome", description="Hệ thống chào mừng phụ")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn Wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "wellcome", "channel", channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh Wellcome: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn Wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "wellcome", "message", message)
        await interaction.response.send_message(f"✅ Đã cập nhật nội dung Wellcome.", ephemeral=True)

    @app_commands.command(name="embed", description="Gán Embed cho hệ thống Wellcome")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        
        update_guild_config(interaction.guild.id, "wellcome", "embed", name)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Wellcome.", ephemeral=True)

    @app_commands.command(name="test", description="Gửi thử tin nhắn Wellcome")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success = await send_wellcome(interaction.guild, interaction.user)
        msg = "✅ Test Wellcome thành công!" if success else "❌ Thất bại: Kiểm tra cấu hình/quyền hạn."
        await interaction.followup.send(msg, ephemeral=True)

# ======================
# LISTENER & INJECTION
# ======================

class WellcomeListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Hệ phụ chạy trong task riêng để bảo vệ Event Loop
        asyncio.create_task(send_wellcome(member.guild, member))

async def setup(bot: commands.Bot):
    # Tiêm lệnh vào /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "wellcome" for c in p_cmd.commands):
            p_cmd.add_command(WellcomeGroup())
    
    await bot.add_cog(WellcomeListener(bot))
    print("[LOAD] Success: core.wellcome (Injected into /p)", flush=True)
