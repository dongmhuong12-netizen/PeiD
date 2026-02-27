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

    try:
        sent_anything = False

        # GỬI MESSAGE TRƯỚC
        if message_text:
            message_text = apply_variables(message_text, guild, member)
            await channel.send(content=message_text)
            sent_anything = True

        # SAU ĐÓ MỚI GỬI EMBED
        if embed_name:
            embed_data = load_embed(embed_name)
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
            f"Đã đặt kênh wellcome: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):

        update_guild_config(interaction.guild.id, "wellcome", "message", message)

        await interaction.response.send_message(
            "Đã cập nhật nội dung wellcome.",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Gán embed")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "wellcome", "embed", name)

        await interaction.response.send_message(
            f"Đã đặt embed wellcome: `{name}`",
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
            "Đã gửi thử." if success else "Chưa cấu hình.",
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
