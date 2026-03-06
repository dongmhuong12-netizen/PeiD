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

    config = get_section(guild.id, section)

    channel_id = config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed")

    if not channel_id:
        return False

    channel = guild.get_channel(channel_id)
    if not channel:
        return False

    try:
        sent_anything = False

        # 🔥 GỬI TEXT TRƯỚC
        if message_text:
            message_text = apply_variables(message_text, guild, member)
            await channel.send(content=message_text)
            sent_anything = True

        # 🔥 GỬI EMBED SAU
        if embed_name:
            embed_data = load_embed(guild.id, embed_name)
            if embed_data:
                await send_embed(
                    channel,
                    embed_data,
                    guild,
                    member
                )
                sent_anything = True

        return sent_anything

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

        if not load_embed(name):
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

        await interaction.followup.send(
            "Test Greet thành công, hãy kiểm tra tại kênh được chỉ định embed." if success else "Lỗi. Không thể Test Greet vì thiếu cấu hình. Hãy đảm bảo rằng Test sau khi có đủ kênh thông báo, text + embed.",
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

        if not load_embed(name):
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

        await interaction.followup.send(
            "Text Leave thành công, hãy kiểm tra tại kênh được chỉ định embed." if success else "Lỗi. Không thể Test Leave vì thiếu cấu hình. Hãy đảm bảo rằng Test sau khi có đủ kênh thông báo, text + embed.",
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
