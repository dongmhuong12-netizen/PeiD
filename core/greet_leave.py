import discord
from discord import app_commands
from discord.ext import commands
import re

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
# LINK TOKEN PARSER
# ======================

def extract_link_tokens(text: str):
    if not text:
        return text, None, None

    label_match = re.search(r'link_label"(.*?)"', text)
    url_match = re.search(r'link_url"(.*?)"', text)

    label = label_match.group(1) if label_match else None
    url = url_match.group(1) if url_match else None

    text = re.sub(r'link_label".*?"', '', text)
    text = re.sub(r'link_url".*?"', '', text)

    return text.strip(), label, url


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

    channel = guild.get_channel(channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(channel_id)
        except:
            return False

    if not isinstance(channel, discord.TextChannel):
        return False

    view = None
    parsed_text = None
    embed = None
    link_label = None
    link_url = None

    # -------- TEXT --------

    if isinstance(message_text, str) and message_text.strip():

        parsed_text = parse_placeholders(message_text, member, channel)
        parsed_text, link_label, link_url = extract_link_tokens(parsed_text)

    # -------- EMBED --------

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

            # 🔥 SỬA Ở ĐÂY: tách link trong embed luôn
            description, embed_label, embed_url = extract_link_tokens(description)

            # nếu text không có link thì lấy link từ embed
            if not link_label and embed_label:
                link_label = embed_label
                link_url = embed_url

            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_data.get("color") or 0x2F3136
            )

            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])

            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=embed_data["thumbnail"])

    # -------- BUTTON --------

    if link_label and link_url:
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=link_label, url=link_url))

    # -------- SEND --------

    if parsed_text and embed:
        await channel.send(content=parsed_text, embed=embed, view=view)
    elif parsed_text:
        await channel.send(content=parsed_text, view=view)
    elif embed:
        await channel.send(embed=embed, view=view)
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

        success = await send_config_message(interaction.guild, interaction.user, "greet")

        if not success:
            await interaction.response.send_message(
                "Chưa cấu hình greet.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Đã gửi test greet.", ephemeral=True
            )


# ======================
# LEAVE GROUP
# ======================

class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="Leave system")

    @app_commands.command(name="channel", description="Set leave channel (Channel ID)")
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

        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã set kênh leave: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="message", description="Set leave message")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):

        update_guild_config(interaction.guild.id, "leave", "message", text)

        await interaction.response.send_message(
            "Đã set message leave.", ephemeral=True
        )

    @app_commands.command(name="embed", description="Set leave embed")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.", ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "leave", "embed", name)

        await interaction.response.send_message(
            f"Đã set embed leave: `{name}`", ephemeral=True
        )

    @app_commands.command(name="test", description="Test leave message")
    async def test(self, interaction: discord.Interaction):

        success = await send_config_message(interaction.guild, interaction.user, "leave")

        if not success:
            await interaction.response.send_message(
                "Chưa cấu hình leave.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Đã gửi test leave.", ephemeral=True
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
