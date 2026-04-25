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

async def send_config_message(guild: discord.Guild, member: discord.Member, section: str):
    """
    Xử lý gửi tin nhắn Greet/Leave tập trung.
    Tối ưu 100k+: Gộp Text và Embed vào 1 request duy nhất (Atomic Send).
    """
    config = get_section(guild.id, section)
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

        # 1. Xử lý TEXT (Apply biến động)
        if message_text:
            final_content = apply_variables(message_text, guild, member)

        # 2. Xử lý EMBED (Đồng bộ với embed_sender)
        if embed_name and perms.embed_links:
            embed_data = load_embed(guild.id, embed_name)
            if embed_data:
                # Sử dụng chuyên gia build Embed đã chốt ở Bước 7
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        # 3. GỬI GỘP (Chống Rate Limit)
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False
    except Exception as e:
        print(f"[GREET/LEAVE ERROR] {section} fail in {guild.id}: {e}", flush=True)
        return False

# ======================
# COMMAND GROUPS
# ======================

class GreetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="greet", description="Cấu hình hệ thống chào mừng")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh Greet: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "greet", "message", message)
        await interaction.response.send_message(f"✅ Đã cập nhật nội dung Greet.", ephemeral=True)

    @app_commands.command(name="embed", description="Gán Embed cho hệ thống Greet")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "greet", "embed", name)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Greet.", ephemeral=True)

    @app_commands.command(name="test", description="Gửi thử tin nhắn chào mừng")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success = await send_config_message(interaction.guild, interaction.user, "greet")
        msg = "✅ Test Greet thành công!" if success else "❌ Thất bại: Kiểm tra cấu hình kênh/quyền."
        await interaction.followup.send(msg, ephemeral=True)

class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="Cấu hình hệ thống tạm biệt")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)
        await interaction.response.send_message(f"✅ Đã đặt kênh Leave: {channel.mention}", ephemeral=True)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn tạm biệt")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "leave", "message", message)
        await interaction.response.send_message(f"✅ Đã cập nhật nội dung Leave.", ephemeral=True)

    @app_commands.command(name="embed", description="Gán Embed cho hệ thống Leave")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(interaction.guild.id, name):
            return await interaction.response.send_message(f"❌ Embed `{name}` không tồn tại.", ephemeral=True)
        update_guild_config(interaction.guild.id, "leave", "embed", name)
        await interaction.response.send_message(f"✅ Đã gán Embed `{name}` cho Leave.", ephemeral=True)

    @app_commands.command(name="test", description="Gửi thử tin nhắn tạm biệt")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success = await send_config_message(interaction.guild, interaction.user, "leave")
        msg = "✅ Test Leave thành công!" if success else "❌ Thất bại: Kiểm tra cấu hình kênh/quyền."
        await interaction.followup.send(msg, ephemeral=True)

# ======================
# LISTENER & SETUP (INJECTION)
# ======================

class GreetLeaveListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        asyncio.create_task(send_config_message(member.guild, member, "greet"))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        asyncio.create_task(send_config_message(member.guild, member, "leave"))

async def setup(bot: commands.Bot):
    # KỸ THUẬT TIÊM LỆNH: Tìm lệnh /p từ Root và cắm Greet/Leave vào
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "greet" for c in p_cmd.commands):
            p_cmd.add_command(GreetGroup())
        if not any(c.name == "leave" for c in p_cmd.commands):
            p_cmd.add_command(LeaveGroup())
    
    await bot.add_cog(GreetLeaveListener(bot))
    print("[LOAD] Success: core.greet_leave (Injected into /p)", flush=True)
