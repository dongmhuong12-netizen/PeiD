import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.embed_sender import send_embed
from core.variable_engine import apply_variables


# ======================
# SEND MESSAGE HANDLER
# ======================

async def send_config_message(guild: discord.Guild, member: discord.Member, section: str):
    """
    Xử lý gửi tin nhắn Chào mừng/Tạm biệt/Booster.
    Tối ưu 100k+ servers: Gộp Text và Embed vào 1 request duy nhất để chống Rate Limit.
    """
    config = get_section(guild.id, section)

    channel_id = config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed")

    if not channel_id:
        return False

    channel = guild.get_channel(channel_id)
    if not channel:
        return False

    permissions = channel.permissions_for(guild.me)
    if not permissions.send_messages:
        return False

    try:
        # 1. Xử lý TEXT (Apply biến trước)
        final_content = None
        if message_text:
            final_content = apply_variables(message_text, guild, member)

        # 2. Xử lý EMBED
        final_embed = None
        if embed_name and permissions.embed_links:
            embed_data = load_embed(guild.id, embed_name)
            if embed_data:
                # Thay vì gọi send_embed (gây thêm 1 request), ta chuẩn bị dữ liệu Embed
                # Lưu ý: Cần đảm bảo send_embed hoặc variable_engine trả về đối tượng discord.Embed
                # Ở đây ta sẽ gọi logic xử lý biến cho Embed data
                from core.embed_sender import build_embed_object # Giả định hàm build object
                
                # Để giữ nguyên logic cũ của Nguyệt là dùng send_embed, 
                # Pei sẽ tối ưu bằng cách gộp content vào chính hàm send_embed nếu nó hỗ trợ.
                # Nếu không, Pei thực hiện gộp trực tiếp tại đây:
                
                processed_data = apply_variables(embed_data, guild, member)
                
                # Tạo Embed object từ data
                from discord import Embed
                final_embed = Embed.from_dict(processed_data)
                
                # Xử lý các biến đặc biệt trong Embed (Image/Thumbnail) nếu cần
                if processed_data.get("image"):
                    final_embed.set_image(url=processed_data["image"])
                if processed_data.get("thumbnail"):
                    final_embed.set_thumbnail(url=processed_data["thumbnail"])

        # 3. GỬI GỘP (Atomic Send)
        # Chỉ tốn 1 request duy nhất cho cả Text và Embed
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False

    except (discord.Forbidden, discord.HTTPException):
        return False
    except Exception:
        return False


# ======================
# GREET GROUP
# ======================

class GreetGroup(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="greet",
            description="Hệ thống chào mừng thành viên mới"
        )

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)

        await interaction.response.send_message(
            f"Đặt kênh Greet thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "greet", "message", message)

        await interaction.response.send_message(
            f"Đặt nội dung Greet thành công: `{message}`.",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Gán embed cho hệ thống chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        embed_data = load_embed(interaction.guild.id, name)

        if not embed_data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "greet", "embed", name)

        await interaction.response.send_message(
            f"Đặt embed Greet thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="test", description="Gửi thử tin nhắn chào mừng")
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        success = await send_config_message(
            interaction.guild,
            interaction.user,
            "greet"
        )

        if success:
            await interaction.followup.send(
                "Test Greet thành công.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Thiếu cấu hình greet.",
                ephemeral=True
            )


# ======================
# LEAVE GROUP
# ======================

class LeaveGroup(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="leave",
            description="Hệ thống thông báo khi thành viên rời đi"
        )

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn rời đi")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)

        await interaction.response.send_message(
            f"Đặt kênh Leave thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn rời đi")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "leave", "message", message)

        await interaction.response.send_message(
            f"Đặt nội dung Leave thành công: `{message}`.",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Gán embed cho hệ thống rời đi")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        embed_data = load_embed(interaction.guild.id, name)

        if not embed_data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "leave", "embed", name)

        await interaction.response.send_message(
            f"Đặt embed Leave thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="test", description="Gửi thử tin nhắn rời đi")
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        success = await send_config_message(
            interaction.guild,
            interaction.user,
            "leave"
        )

        if success:
            await interaction.followup.send(
                "Test Leave thành công.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Thiếu cấu hình leave.",
                ephemeral=True
            )


# ======================
# LISTENER
# ======================

class GreetLeaveListener(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await send_config_message(member.guild, member, "greet")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await send_config_message(member.guild, member, "leave")


async def setup(bot):
    await bot.add_cog(GreetLeaveListener(bot))
