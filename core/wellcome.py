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

async def send_wellcome(guild: discord.Guild, member: discord.Member):

    config = get_section(guild.id, "wellcome")

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

    sent_anything = False

    try:

        # TEXT
        if message_text:
            message_text = apply_variables(message_text, guild, member)
            await channel.send(content=message_text)
            sent_anything = True

        # EMBED
        if embed_name and permissions.embed_links:

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

    except discord.Forbidden:
        return False

    except discord.HTTPException:
        return False


# ======================
# GROUP
# ======================

class WellcomeGroup(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="wellcome",
            description="Hệ chào mừng phụ"
        )

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        update_guild_config(interaction.guild.id, "wellcome", "channel", channel.id)

        await interaction.response.send_message(
            f"Đặt kênh Wellcome thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "wellcome", "message", message)

        await interaction.response.send_message(
            f"Đặt nội dung Wellcome thành công: '{message}'.",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Gán embed")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        embed_data = load_embed(interaction.guild.id, name)

        if not embed_data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "wellcome", "embed", name)

        await interaction.response.send_message(
            f"Đặt embed Wellcome thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="test", description="Gửi thử")
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        success = await send_wellcome(
            interaction.guild,
            interaction.user
        )

        await interaction.followup.send(
            "Test Wellcome thành công." if success else "Thiếu cấu hình Wellcome.",
            ephemeral=True
        )


# ======================
# LISTENER
# ======================

class WellcomeListener(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        await send_wellcome(member.guild, member)
