import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed


# ======================
# SEND MESSAGE HANDLER
# ======================

async def send_config_message(guild: discord.Guild, member: discord.Member, section: str):

    config = get_section(guild.id, section)

    channel_id = config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed")

    if not channel_id:
        return False

    channel = guild.get_channel(channel_id)
    if not channel:
        return False

    embed_obj = None

    if embed_name:
        embed_data = load_embed(embed_name)
        if embed_data:
            embed_obj = discord.Embed.from_dict(embed_data)

    if message_text:
        message_text = (
            message_text
            .replace("{user}", member.mention)
            .replace("{server}", guild.name)
            .replace("{member_count}", str(guild.member_count))
        )

    try:
        await channel.send(content=message_text, embed=embed_obj)
        return True
    except:
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

    @app_commands.command(
        name="channel",
        description="Đặt kênh gửi tin nhắn chào mừng"
    )
    @app_commands.describe(
        channel="Chọn kênh sẽ gửi tin nhắn khi có thành viên mới"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã đặt kênh chào mừng: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(
        name="message",
        description="Đặt nội dung tin nhắn chào mừng"
    )
    @app_commands.describe(
        message="Có thể dùng {user}, {server}, {member_count}"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "greet", "message", message)

        await interaction.response.send_message(
            "Đã cập nhật nội dung chào mừng.",
            ephemeral=True
        )

    @app_commands.command(
        name="embed",
        description="Gán embed đã tạo cho hệ thống chào mừng"
    )
    @app_commands.describe(
        name="Tên embed đã lưu bằng lệnh /p embed create"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "greet", "embed", name)

        await interaction.response.send_message(
            f"Đã đặt embed chào mừng: `{name}`",
            ephemeral=True
        )

    @app_commands.command(
        name="test",
        description="Kiểm tra hệ thống chào mừng (gửi thử tin nhắn)"
    )
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        success = await send_config_message(
            interaction.guild,
            interaction.user,
            "greet"
        )

        if not success:
            await interaction.followup.send(
                "Chưa cấu hình hệ thống chào mừng.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Đã gửi tin nhắn chào mừng thử.",
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

    @app_commands.command(
        name="channel",
        description="Đặt kênh gửi tin nhắn khi thành viên rời đi"
    )
    @app_commands.describe(
        channel="Chọn kênh sẽ gửi tin nhắn khi có người rời server"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã đặt kênh rời đi: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(
        name="message",
        description="Đặt nội dung tin nhắn rời đi"
    )
    @app_commands.describe(
        message="Có thể dùng {user}, {server}"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "leave", "message", message)

        await interaction.response.send_message(
            "Đã cập nhật nội dung rời đi.",
            ephemeral=True
        )

    @app_commands.command(
        name="embed",
        description="Gán embed đã tạo cho hệ thống rời đi"
    )
    @app_commands.describe(
        name="Tên embed đã lưu bằng lệnh /p embed create"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "leave", "embed", name)

        await interaction.response.send_message(
            f"Đã đặt embed rời đi: `{name}`",
            ephemeral=True
        )

    @app_commands.command(
        name="test",
        description="Kiểm tra hệ thống rời đi (gửi thử tin nhắn)"
    )
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        success = await send_config_message(
            interaction.guild,
            interaction.user,
            "leave"
        )

        if not success:
            await interaction.followup.send(
                "Chưa cấu hình hệ thống rời đi.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Đã gửi tin nhắn rời đi thử.",
                ephemeral=True
            )
