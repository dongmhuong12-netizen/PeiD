import discord
from discord.ext import commands
from discord import app_commands
import random

PERSONAL_GUILD_ID = 1111391147030482944

DEFAULT_COLOR = 0xf48fb1
DEFAULT_TITLE = "Woaaaa!! ⋆˚⟡˖ ࣪"
DEFAULT_MESSAGE = "then kiu {user} đã boost server này nha ✨"

DEFAULT_GIFS = [
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
]

# Lưu config tạm (sau này có thể thay bằng database)
guild_config = {}

class BoosterV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_config(self, guild_id):
        return guild_config.get(guild_id, {})

    def set_config(self, guild_id, key, value):
        if guild_id not in guild_config:
            guild_config[guild_id] = {}
        guild_config[guild_id][key] = value

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        # Không xử lý server cá nhân (V1 lo)
        if after.guild.id == PERSONAL_GUILD_ID:
            return

        config = self.get_config(after.guild.id)

        role_id = config.get("role")
        channel_id = config.get("channel")
        message = config.get("message", DEFAULT_MESSAGE)
        gifs = config.get("gifs", DEFAULT_GIFS)

        role = after.guild.get_role(role_id) if role_id else None
        channel = after.guild.get_channel(channel_id) if channel_id else after.guild.system_channel

        if not channel:
            return

        # Boost
        if before.premium_since is None and after.premium_since is not None:

            if role:
                await after.add_roles(role)

            embed = discord.Embed(
                title=DEFAULT_TITLE,
                description=message.replace("{user}", after.mention),
                color=DEFAULT_COLOR
            )
            embed.set_image(url=random.choice(gifs))
            await channel.send(embed=embed)

        # Unboost
        if before.premium_since is not None and after.premium_since is None:

            if role and role in after.roles:
                await after.remove_roles(role)

    # ---------------- SLASH COMMANDS ----------------

    @app_commands.command(name="testboost", description="Test hệ thống boost V2")
    async def testboost(self, interaction: discord.Interaction):
        await interaction.response.send_message("Boost V2 hoạt động 🌍", ephemeral=True)

    @app_commands.command(name="setrole", description="Set role boost")
    @app_commands.checks.has_permissions(administrator=True)
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        self.set_config(interaction.guild.id, "role", role.id)
        await interaction.response.send_message(f"Đã set role boost: {role.name}", ephemeral=True)

    @app_commands.command(name="setchannel", description="Set kênh gửi thông báo boost")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.set_config(interaction.guild.id, "channel", channel.id)
        await interaction.response.send_message(f"Đã set kênh: {channel.mention}", ephemeral=True)

    @app_commands.command(name="setmessgener", description="Set nội dung message boost")
    @app_commands.checks.has_permissions(administrator=True)
    async def setmessage(self, interaction: discord.Interaction, message: str):
        self.set_config(interaction.guild.id, "message", message)
        await interaction.response.send_message("Đã cập nhật message boost.", ephemeral=True)

    @app_commands.command(name="imagelink", description="Thêm link GIF boost")
    @app_commands.checks.has_permissions(administrator=True)
    async def imagelink(self, interaction: discord.Interaction, link: str):

        config = self.get_config(interaction.guild.id)
        gifs = config.get("gifs", DEFAULT_GIFS.copy())

        gifs.append(link)
        self.set_config(interaction.guild.id, "gifs", gifs)

        await interaction.response.send_message("Đã thêm GIF mới.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BoosterV2(bot))
