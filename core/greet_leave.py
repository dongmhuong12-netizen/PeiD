import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed


# ======================
# PLACEHOLDER PARSER
# ======================

def parse_placeholders(text: str, member: discord.Member, channel: discord.TextChannel):
    if not text:
        return text

    guild = member.guild

    replacements = {
        "{user}": member.mention,
        "{username}": member.name,
        "{server}": guild.name if guild else "",
        "{membercount}": str(guild.member_count) if guild else "0",
        "{channel}": channel.mention if channel else "",
        "{top_role}": member.top_role.mention if member.top_role else "",
        "{server_icon}": guild.icon.url if guild and guild.icon else ""
    }

    for key, value in replacements.items():
        text = text.replace(key, value)

    return text


# ======================
# SEND FUNCTION
# ======================

async def send_config_message(guild, member, section_name):
    config = get_section(guild.id, section_name)

    channel_id = config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed")

    if not channel_id:
        return False

    # LẤY CHANNEL (ANTI CACHE)
    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except:
            return False

    if not isinstance(channel, discord.TextChannel):
        return False

    # ======================
    # TEXT
    # ======================

    parsed_text = None
    if isinstance(message_text, str) and message_text.strip():
        parsed_text = parse_placeholders(message_text, member, channel)

    # ======================
    # EMBED
    # ======================

    embed = None
    if isinstance(embed_name, str) and embed_name.strip():
        embed_data = load_embed(embed_name)

        if isinstance(embed_data, dict):

            title = parse_placeholders(
                embed_data.get("title", ""),
                member,
                channel
            )

            description = parse_placeholders(
                embed_data.get("description", ""),
                member,
                channel
            )

            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_data.get("color") or 0x2F3136
            )

            # Image
            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])

            # Thumbnail
            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=embed_data["thumbnail"])

    # ======================
    # SEND
    # ======================

    if parsed_text and embed:
        await channel.send(content=parsed_text, embed=embed)

    elif parsed_text:
        await channel.send(content=parsed_text)

    elif embed:
        await channel.send(embed=embed)

    else:
        return False

    return True


# ======================
# GREET GROUP
# ======================

class GreetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="greet", description="Greet system")

    @app_commands.command(name="channel", description="Set greet channel (Channel ID)")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_id: str):

        if not channel_id.isdigit():
            await interaction.response.send_message(
                "Channel ID không hợp lệ.", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Không tìm thấy text channel với ID đó.", ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã set kênh greet: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="message", description="Set greet message")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):

        update_guild_config(interaction.guild.id, "greet", "message", text)

        await interaction.response.send_message(
            "Đã set message greet.", ephemeral=True
        )

    @app_commands.command(name="embed", description="Set greet embed")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.", ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "greet", "embed", name)

        await interaction.response.send_message(
            f"Đã set embed greet: `{name}`", ephemeral=True
        )

    @app_commands.command(name="test", description="Test greet message")
    async def test(self, interaction: discord.Interaction):

        member = interaction.user

        success = await send_config_message(interaction.guild, member, "greet")

        if not success:
            await interaction.response.send_message(
                "Chưa cấu hình greet.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Đã gửi test greet.", ephemeral=True
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
