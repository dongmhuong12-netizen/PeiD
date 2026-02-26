import discord
from discord import app_commands
from discord.ext import commands

from greet_storage import get_section, update_guild_config
from embed_storage import load_embed


class GreetLeave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ======================
    # Placeholder Parser
    # ======================

    def parse_placeholders(self, text: str, member: discord.Member, channel: discord.TextChannel):
        if not text:
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
    # Greet Commands
    # ======================

    @app_commands.command(name="greet_set_channel", description="Set greet channel")
    async def greet_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "greet", "channel", channel.id)
        await interaction.response.send_message(f"Đã set kênh greet: {channel.mention}", ephemeral=True)

    @app_commands.command(name="greet_set_embed", description="Set greet embed")
    async def greet_set_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(name):
            await interaction.response.send_message(f"Embed tên {name} không tồn tại.", ephemeral=True)
            return

        update_guild_config(interaction.guild.id, "greet", "embed", name)
        await interaction.response.send_message(f"Đã set embed greet: {name}", ephemeral=True)

    @app_commands.command(name="greet_set_message", description="Set greet message")
    async def greet_set_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "greet", "message", text)
        await interaction.response.send_message("Đã set message greet.", ephemeral=True)

    @app_commands.command(name="greet_test", description="Test greet message")
    async def greet_test(self, interaction: discord.Interaction):
        config = get_section(interaction.guild.id, "greet")

        channel_id = config.get("channel")
        embed_name = config.get("embed")
        message_text = config.get("message")

        if not channel_id:
            await interaction.response.send_message("Chưa set kênh greet.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Không tìm thấy kênh greet.", ephemeral=True)
            return

        parsed_text = self.parse_placeholders(message_text, interaction.user, channel)

        embed = None
        if embed_name:
            embed_data = load_embed(embed_name)
            if embed_data:
                embed = discord.Embed.from_dict(embed_data)

        await channel.send(content=parsed_text, embed=embed)
        await interaction.response.send_message("Đã gửi test greet.", ephemeral=True)

    # ======================
    # Leave Commands
    # ======================

    @app_commands.command(name="leave_set_channel", description="Set leave channel")
    async def leave_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        update_guild_config(interaction.guild.id, "leave", "channel", channel.id)
        await interaction.response.send_message(f"Đã set kênh leave: {channel.mention}", ephemeral=True)

    @app_commands.command(name="leave_set_embed", description="Set leave embed")
    async def leave_set_embed(self, interaction: discord.Interaction, name: str):
        if not load_embed(name):
            await interaction.response.send_message(f"Embed tên {name} không tồn tại.", ephemeral=True)
            return

        update_guild_config(interaction.guild.id, "leave", "embed", name)
        await interaction.response.send_message(f"Đã set embed leave: {name}", ephemeral=True)

    @app_commands.command(name="leave_set_message", description="Set leave message")
    async def leave_set_message(self, interaction: discord.Interaction, text: str):
        update_guild_config(interaction.guild.id, "leave", "message", text)
        await interaction.response.send_message("Đã set message leave.", ephemeral=True)

    @app_commands.command(name="leave_test", description="Test leave message")
    async def leave_test(self, interaction: discord.Interaction):
        config = get_section(interaction.guild.id, "leave")

        channel_id = config.get("channel")
        embed_name = config.get("embed")
        message_text = config.get("message")

        if not channel_id:
            await interaction.response.send_message("Chưa set kênh leave.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Không tìm thấy kênh leave.", ephemeral=True)
            return

        parsed_text = self.parse_placeholders(message_text, interaction.user, channel)

        embed = None
        if embed_name:
            embed_data = load_embed(embed_name)
            if embed_data:
                embed = discord.Embed.from_dict(embed_data)

        await channel.send(content=parsed_text, embed=embed)
        await interaction.response.send_message("Đã gửi test leave.", ephemeral=True)

    # ======================
    # Events
    # ======================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = get_section(member.guild.id, "greet")

        channel_id = config.get("channel")
        embed_name = config.get("embed")
        message_text = config.get("message")

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        parsed_text = self.parse_placeholders(message_text, member, channel)

        embed = None
        if embed_name:
            embed_data = load_embed(embed_name)
            if embed_data:
                embed = discord.Embed.from_dict(embed_data)

        await channel.send(content=parsed_text, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = get_section(member.guild.id, "leave")

        channel_id = config.get("channel")
        embed_name = config.get("embed")
        message_text = config.get("message")

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        parsed_text = self.parse_placeholders(message_text, member, channel)

        embed = None
        if embed_name:
            embed_data = load_embed(embed_name)
            if embed_data:
                embed = discord.Embed.from_dict(embed_data)

        await channel.send(content=parsed_text, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GreetLeave(bot))
