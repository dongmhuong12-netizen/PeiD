import discord
from discord.ext import commands
from discord import app_commands
import random
import sqlite3
import json

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
        self.db = sqlite3.connect("booster.db")
        self.cursor = self.db.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS booster_config (
                guild_id TEXT PRIMARY KEY,
                channel_id INTEGER,
                role_id INTEGER,
                message TEXT,
                gifs TEXT
            )
        """)
        self.db.commit()

    def get_config(self, guild_id):
        self.cursor.execute("SELECT * FROM booster_config WHERE guild_id = ?", (str(guild_id),))
        data = self.cursor.fetchone()

        if not data:
            return None, None, DEFAULT_MESSAGE, DEFAULT_GIFS.copy()

        _, channel_id, role_id, message, gifs = data
        gifs = json.loads(gifs) if gifs else DEFAULT_GIFS.copy()

        return role_id, channel_id, message or DEFAULT_MESSAGE, gifs

    def update_config(self, guild_id, channel=None, role=None, message=None, gifs=None):
        role_id, channel_id, old_message, old_gifs = self.get_config(guild_id)

        channel_id = channel if channel is not None else channel_id
        role_id = role if role is not None else role_id
        message = message if message is not None else old_message
        gifs = gifs if gifs is not None else old_gifs

        self.cursor.execute("""
            INSERT OR REPLACE INTO booster_config
            (guild_id, channel_id, role_id, message, gifs)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(guild_id),
            channel_id,
            role_id,
            message,
            json.dumps(gifs)
        ))
        self.db.commit()

    async def send_boost_banner(self, member: discord.Member):
        role_id, channel_id, message, gifs = self.get_config(member.guild.id)

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="Sever Booster!!",
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

    # ===== ADMIN CHECK =====

    async def admin_only(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Chỉ admin mới dùng được lệnh này!",
                ephemeral=True
            )
            return False
        return True

    # ===== COMMANDS =====

    @app_commands.command(name="setchannel")
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.admin_only(interaction): return
        self.update_config(interaction.guild.id, channel=channel.id)
        await interaction.response.send_message("Đã set channel!", ephemeral=True)

    @app_commands.command(name="setrole")
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        if not await self.admin_only(interaction): return
        self.update_config(interaction.guild.id, role=role.id)
        await interaction.response.send_message("Đã set role!", ephemeral=True)

    @app_commands.command(name="setmessenger")
    async def setmessenger(self, interaction: discord.Interaction, message: str):
        if not await self.admin_only(interaction): return
        self.update_config(interaction.guild.id, message=message)
        await interaction.response.send_message("Đã set message mới!", ephemeral=True)

    @app_commands.command(name="imagelink")
    async def imagelink(self, interaction: discord.Interaction, link: str):
        if not await self.admin_only(interaction): return
        role_id, channel_id, message, gifs = self.get_config(interaction.guild.id)
        gifs.append(link)
        self.update_config(interaction.guild.id, gifs=gifs)
        await interaction.response.send_message("Đã thêm GIF!", ephemeral=True)

    @app_commands.command(name="testboost")
    async def testboost(self, interaction: discord.Interaction):
        if not await self.admin_only(interaction): return
        await interaction.response.send_message("Đã gửi banner test!", ephemeral=True)
        await self.send_boost_banner(interaction.user)


async def setup(bot):
    await bot.add_cog(Booster(bot))
