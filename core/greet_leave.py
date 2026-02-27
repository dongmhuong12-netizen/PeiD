import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
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

    # Apply variables to message
    if message_text:
        message_text = apply_variables(message_text, guild, member)

    embed_obj = None

    # Apply variables to embed
    if embed_name:
        embed_data = load_embed(embed_name)
        if embed_data:
            embed_data = apply_variables(embed_data, guild, member)
            embed_obj = discord.Embed.from_dict(embed_data)

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

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã đặt kênh chào mừng: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn chào mừng")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "greet", "message", message)

        await interaction.response.send_message(
            "Đã cập nhật nội dung chào mừng.",
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
            f"Đã đặt embed chào mừng: `{name}`",
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
            "Đã gửi thử." if success else "Chưa cấu hình.",
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
            f"Đã đặt kênh rời đi: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn rời đi")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "leave", "message", message)

        await interaction.response.send_message(
            "Đã cập nhật nội dung rời đi.",
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
            f"Đã đặt embed rời đi: `{name}`",
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
            "Đã gửi thử." if success else "Chưa cấu hình.",
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
