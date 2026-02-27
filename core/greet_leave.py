import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed


# ======================
# PLACEHOLDER PARSER
# ======================

def parse_placeholders(text: str, member: discord.Member, channel: discord.TextChannel):
    if text is None:
        return None

    return (
        text
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
        .replace("{channel}", channel.mention)
        .replace("{top_role}", member.top_role.mention if member.top_role else "")
        .replace("{server_icon}", member.guild.icon.url if member.guild.icon else "")
    )


# ======================
# HELPER SEND FUNCTION
# ======================

async def send_config_message(guild, member, section_name):
    config = get_section(guild.id, section_name)

    channel_id = config.get("channel")
    embed_name = config.get("embed")
    message_text = config.get("message")

    if not channel_id:
        return False

    channel = guild.get_channel(channel_id)
    if not channel:
        return False

    parsed_text = parse_placeholders(message_text, member, channel) if message_text else None

    embed = None
    if embed_name:
        embed_data = load_embed(embed_name)
        if embed_data:
            embed = discord.Embed(
                title=embed_data.get("title"),
                description=embed_data.get("description"),
                color=embed_data.get("color") or 0x2F3136
            )
            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])

    if not parsed_text and not embed:
        return False

    await channel.send(content=parsed_text, embed=embed)
    return True


# ======================
# GREET SET GROUP
# ======================

class GreetSetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="set", description="Set greet configuration")

    @app_commands.command(name="channel", description="Set greet channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)
        await interaction.response.send_message(
            f"Đã set kênh greet: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="embed", description="Set greet embed")
    async def set_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.", ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "greet", "embed", name)
        await interaction.response.send_message(
            f"Đã set embed greet: `{name}`", ephemeral=True
        )

    @app_commands.command(name="message", description="Set greet message")
    async def set_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "greet", "message", text)
        await interaction.response.send_message(
            "Đã set message greet.", ephemeral=True
        )


# ======================
# GREET GROUP
# ======================

class GreetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="greet", description="Greet system")
        self.add_command(GreetSetGroup())

    @app_commands.command(name="test", description="Test greet message")
    async def test(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)

        success = await send_config_message(interaction.guild, member, "greet")

        if not success:
            await interaction.response.send_message(
                "Chưa cấu hình greet đầy đủ.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Đã gửi test greet.", ephemeral=True
            )


# ======================
# LEAVE SET GROUP
# ======================

class LeaveSetGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="set", description="Set leave configuration")

    @app_commands.command(name="channel", description="Set leave channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)
        await interaction.response.send_message(
            f"Đã set kênh leave: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="embed", description="Set leave embed")
    async def set_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.", ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "leave", "embed", name)
        await interaction.response.send_message(
            f"Đã set embed leave: `{name}`", ephemeral=True
        )

    @app_commands.command(name="message", description="Set leave message")
    async def set_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "leave", "message", text)
        await interaction.response.send_message(
            "Đã set message leave.", ephemeral=True
        )


# ======================
# LEAVE GROUP
# ======================

class LeaveGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="leave", description="Leave system")
        self.add_command(LeaveSetGroup())

    @app_commands.command(name="test", description="Test leave message")
    async def test(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)

        success = await send_config_message(interaction.guild, member, "leave")

        if not success:
            await interaction.response.send_message(
                "Chưa cấu hình leave đầy đủ.", ephemeral=True
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
