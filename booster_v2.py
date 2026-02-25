import discord
from discord.ext import commands
from discord import app_commands
import random

DEFAULT_COLOR = 0xf48fb1

DEFAULT_MESSAGE = "then kiu {user} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡"

DEFAULT_GIFS = [
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
]


class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_config = {}

    def get_config(self, guild_id):
        config = self.guild_config.get(guild_id, {})
        return (
            config.get("role"),
            config.get("channel"),
            config.get("message", DEFAULT_MESSAGE),
            config.get("gifs", DEFAULT_GIFS.copy()),
        )

    async def send_boost_banner(self, member: discord.Member):
        role_id, channel_id, message, gifs = self.get_config(member.guild.id)

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="Woaaaa!! ⋆˚⟡˖ ࣪",
            description=message.format(user=member.mention),
            color=DEFAULT_COLOR
        )

        embed.set_image(url=random.choice(gifs))
        await channel.send(embed=embed)

        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.premium_since and after.premium_since:
            await self.send_boost_banner(after)

        if before.premium_since and not after.premium_since:
            role_id, _, _, _ = self.get_config(after.guild.id)
            if role_id:
                role = after.guild.get_role(role_id)
                if role:
                    try:
                        await after.remove_roles(role)
                    except:
                        pass

    # ===== SLASH COMMANDS =====

    @app_commands.command(name="testboost", description="Test banner boost")
    async def testboost(self, interaction: discord.Interaction):
        await interaction.response.send_message("Đã gửi banner test!", ephemeral=True)
        await self.send_boost_banner(interaction.user)

    @app_commands.command(name="setchannel", description="Set kênh gửi banner")
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.guild_config.setdefault(interaction.guild.id, {})
        self.guild_config[interaction.guild.id]["channel"] = channel.id
        await interaction.response.send_message("Đã set channel!", ephemeral=True)

    @app_commands.command(name="setrole", description="Set role boost")
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        self.guild_config.setdefault(interaction.guild.id, {})
        self.guild_config[interaction.guild.id]["role"] = role.id
        await interaction.response.send_message("Đã set role!", ephemeral=True)

    @app_commands.command(name="setmessage", description="Set nội dung banner")
    async def setmessage(self, interaction: discord.Interaction, message: str):
        self.guild_config.setdefault(interaction.guild.id, {})
        self.guild_config[interaction.guild.id]["message"] = message
        await interaction.response.send_message("Đã set message!", ephemeral=True)

    @app_commands.command(name="imagelink", description="Thêm link GIF cho banner")
    async def imagelink(self, interaction: discord.Interaction, link: str):
        self.guild_config.setdefault(interaction.guild.id, {})
        gifs = self.guild_config[interaction.guild.id].setdefault("gifs", DEFAULT_GIFS.copy())

        gifs.append(link)

        await interaction.response.send_message("Đã thêm GIF mới!", ephemeral=True)

    @app_commands.command(name="resetgif", description="Reset lại GIF mặc định")
    async def resetgif(self, interaction: discord.Interaction):
        self.guild_config.setdefault(interaction.guild.id, {})
        self.guild_config[interaction.guild.id]["gifs"] = DEFAULT_GIFS.copy()
        await interaction.response.send_message("Đã reset về 6 GIF mặc định!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Booster(bot))
