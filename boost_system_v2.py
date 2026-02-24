import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

CONFIG_FILE = "boost_config.json"

# ===== DEFAULT PEID SYSTEM =====
DEFAULT_TITLE = "⋆˚⟡˖ ࣪ PeiD Booster ✨"
DEFAULT_MESSAGE = "Woaaaa!! ⋆˚⟡˖ ࣪\n\nCảm ơn {user} đã buff cho PeiD nha, iu nhắm nhắm ݁ ˖Ი𐑼⋆‧♡♡"
DEFAULT_COLOR = 0xf48fb1

DEFAULT_IMAGES = [
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931963880771624/E589A5AB-D017-4D3B-BD89-28C9E88E8F44.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931923162599556/BCFAAC06-A222-48EE-BEA7-4A98EC1439FA.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931820414472392/636F6298-A72D-43FD-AD7E-11BB0EA142E6.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931736482250802/8B8F60E8-4154-49A3-B208-7D3139A6230E.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931661899399178/472DCFEC-EA85-41FB-94DF-F21D8A788497.gif",
    "https://cdn.discordapp.com/attachments/1475931488485900288/1475931584002654230/D6107690-3456-4205-9563-EE691F4DFCB5.gif",
]


# ===== LOAD / SAVE CONFIG =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class BoostSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()

    # =============================
    # BOOST EVENT LISTENER
    # =============================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.guild is None:
            return

        guild_id = str(after.guild.id)

        if guild_id not in self.config:
            return

        guild_config = self.config[guild_id]

        role_id = guild_config.get("boost_role")
        if not role_id:
            return

        role = after.guild.get_role(role_id)
        if not role:
            return

        # NEW BOOST
        if not before.premium_since and after.premium_since:
            await after.add_roles(role)

            channel_id = guild_config.get("boost_channel")
            if channel_id:
                channel = after.guild.get_channel(channel_id)
                if channel:
                    message = guild_config.get("boost_message", DEFAULT_MESSAGE)
                    images = guild_config.get("boost_images", DEFAULT_IMAGES)

                    embed = discord.Embed(
                        title=DEFAULT_TITLE,
                        description=message.format(user=after.mention),
                        color=DEFAULT_COLOR
                    )

                    embed.set_image(url=random.choice(images))
                    await channel.send(embed=embed)

        # BOOST REMOVED
        if before.premium_since and not after.premium_since:
            if role in after.roles:
                await after.remove_roles(role)

    # =============================
    # SLASH COMMAND GROUP
    # =============================
    boost = app_commands.Group(name="boost", description="Boost system setup")

    @boost.command(name="setrole", description="Set boost role")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id]["boost_role"] = role.id
        save_config(self.config)

        await interaction.response.send_message("✅ Boost role đã được set.", ephemeral=True)

    @boost.command(name="setchannel", description="Set boost channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id]["boost_channel"] = channel.id
        save_config(self.config)

        await interaction.response.send_message("✅ Boost channel đã được set.", ephemeral=True)

    @boost.command(name="setmessage", description="Set custom boost message")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setmessage(self, interaction: discord.Interaction, message: str):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id]["boost_message"] = message
        save_config(self.config)

        await interaction.response.send_message("✅ Boost message đã được set.", ephemeral=True)

    @boost.command(name="setimage", description="Add custom boost gif")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setimage(self, interaction: discord.Interaction, link: str):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {}

        if "boost_images" not in self.config[guild_id]:
            self.config[guild_id]["boost_images"] = []

        self.config[guild_id]["boost_images"].append(link)
        save_config(self.config)

        await interaction.response.send_message("✅ Đã thêm gif boost.", ephemeral=True)

    @boost.command(name="testboost", description="Test boost system")
    async def testboost(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        guild_config = self.config.get(guild_id, {})

        message = guild_config.get("boost_message", DEFAULT_MESSAGE)
        images = guild_config.get("boost_images", DEFAULT_IMAGES)

        embed = discord.Embed(
            title=DEFAULT_TITLE,
            description=message.format(user=interaction.user.mention),
            color=DEFAULT_COLOR
        )

        embed.set_image(url=random.choice(images))

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(BoostSystem(bot))
