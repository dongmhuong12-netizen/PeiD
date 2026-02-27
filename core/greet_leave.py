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

    label_match = re.search(r'link_label\s*"(.*?)"', text, re.IGNORECASE)
    url_match = re.search(r'link_url\s*"(.*?)"', text, re.IGNORECASE)

    label = label_match.group(1).strip() if label_match else None
    url = url_match.group(1).strip() if url_match else None

    text = re.sub(r'link_label\s*".*?"', '', text, flags=re.IGNORECASE)
    text = re.sub(r'link_url\s*".*?"', '', text, flags=re.IGNORECASE)

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

    # -------- TEXT --------
    if isinstance(message_text, str) and message_text.strip():

        parsed_text = parse_placeholders(message_text, member, channel)
        parsed_text, link_label, link_url = extract_link_tokens(parsed_text)

        if link_label and link_url:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=link_label, url=link_url))

    # -------- EMBED --------
    embed = None

    if isinstance(embed_name, str) and embed_name.strip():
        embed_data = load_embed(embed_name)

        if isinstance(embed_data, dict):

            title = embed_data.get("title", "")
            description = embed_data.get("description", "")

            title = parse_placeholders(title, member, channel)
            description = parse_placeholders(description, member, channel)

            description, link_label, link_url = extract_link_tokens(description)

            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_data.get("color") or 0x2F3136
            )

            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])

            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=embed_data["thumbnail"])

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


# =====================================================
#                COMMAND GROUPS
# =====================================================

class GreetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="greet", description="Greeting system")

    @app_commands.command(name="channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)
        await interaction.response.send_message("Đã cập nhật kênh chào mừng.", ephemeral=True)

    @app_commands.command(name="message")
    async def set_message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "greet", "message", message)
        await interaction.response.send_message("Đã cập nhật nội dung chào mừng.", ephemeral=True)

    @app_commands.command(name="embed")
    async def set_embed(self, interaction: discord.Interaction, name: str):
        update_guild_config(interaction.guild.id, "greet", "embed", name)
        await interaction.response.send_message("Đã cập nhật embed chào mừng.", ephemeral=True)


class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="Leave system")

    @app_commands.command(name="channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)
        await interaction.response.send_message("Đã cập nhật kênh rời đi.", ephemeral=True)

    @app_commands.command(name="message")
    async def set_message(self, interaction: discord.Interaction, message: str):
        update_guild_config(interaction.guild.id, "leave", "message", message)
        await interaction.response.send_message("Đã cập nhật nội dung rời đi.", ephemeral=True)

    @app_commands.command(name="embed")
    async def set_embed(self, interaction: discord.Interaction, name: str):
        update_guild_config(interaction.guild.id, "leave", "embed", name)
        await interaction.response.send_message("Đã cập nhật embed rời đi.", ephemeral=True)


# =====================================================
#                LISTENER
# =====================================================

class GreetLeaveListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await send_config_message(member.guild, member, "greet")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await send_config_message(member.guild, member, "leave")
