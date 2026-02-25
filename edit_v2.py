import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime

DB_FILE = "edit_v2_data.json"


def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def ensure_guild(db, gid):
    if gid not in db:
        db[gid] = {
            "enabled": False,
            "channel": None,
            "greet": None,
            "leave": None,
            "dm_greet": False,
            "delay": 0,
            "cooldown": 0,
            "last_join": 0,
            "embeds": {},
        }


def parse_variables(text: str, member: discord.Member):
    return (
        text.replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{userid}", str(member.id))
        .replace("{server}", member.guild.name)
        .replace("{membercount}", str(member.guild.member_count))
        .replace("{created_at}", member.created_at.strftime("%d/%m/%Y"))
        .replace("{joined_at}", member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Unknown")
    )


def hex_to_color(hex_str):
    try:
        return discord.Color(int(hex_str.replace("#", ""), 16))
    except:
        return discord.Color.blue()


class EditModal(discord.ui.Modal, title="Chỉnh sửa Description"):
    new_desc = discord.ui.TextInput(label="Description mới", style=discord.TextStyle.paragraph)

    def __init__(self, profile_name):
        super().__init__()
        self.profile_name = profile_name

    async def on_submit(self, interaction: discord.Interaction):
        db = load_db()
        gid = str(interaction.guild.id)
        db[gid]["embeds"][self.profile_name]["description"] = self.new_desc.value
        save_db(db)
        await interaction.response.send_message("Đã cập nhật description.", ephemeral=True)


class TestView(discord.ui.View):
    def __init__(self, profile):
        super().__init__(timeout=60)
        self.profile = profile

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditModal(self.profile))


class EditV2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= TOGGLE =================

    @app_commands.command(name="toggle")
    async def toggle(self, interaction: discord.Interaction, mode: str):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["enabled"] = mode.lower() == "on"
        save_db(db)
        await interaction.response.send_message(f"Hệ thống: {mode.upper()}", ephemeral=True)

    # ================= SETTINGS =================

    @app_commands.command(name="setchannel")
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["channel"] = channel.id
        save_db(db)
        await interaction.response.send_message("Đã set kênh.", ephemeral=True)

    @app_commands.command(name="setdelay")
    async def setdelay(self, interaction: discord.Interaction, seconds: int):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["delay"] = seconds
        save_db(db)
        await interaction.response.send_message(f"Delay: {seconds}s", ephemeral=True)

    @app_commands.command(name="setcooldown")
    async def setcooldown(self, interaction: discord.Interaction, seconds: int):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["cooldown"] = seconds
        save_db(db)
        await interaction.response.send_message(f"Cooldown: {seconds}s", ephemeral=True)

    @app_commands.command(name="setdm")
    async def setdm(self, interaction: discord.Interaction, mode: str):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["dm_greet"] = mode.lower() == "on"
        save_db(db)
        await interaction.response.send_message("DM greet updated.", ephemeral=True)

    # ================= EMBED =================

    @app_commands.command(name="createembed")
    async def createembed(self, interaction: discord.Interaction, name: str, title: str, description: str):
        db = load_db()
        gid = str(interaction.guild.id)
        ensure_guild(db, gid)

        db[gid]["embeds"][name] = {
            "title": title,
            "description": description,
            "color": "#3498db",
        }

        save_db(db)
        await interaction.response.send_message("Embed created.", ephemeral=True)

    @app_commands.command(name="testembed")
    async def testembed(self, interaction: discord.Interaction, name: str):
        db = load_db()
        gid = str(interaction.guild.id)

        data = db.get(gid, {}).get("embeds", {}).get(name)
        if not data:
            await interaction.response.send_message("Không tồn tại.", ephemeral=True)
            return

        embed = self.build_embed(data, interaction.user)
        await interaction.response.send_message(embed=embed, view=TestView(name))

    def build_embed(self, data, member):
        embed = discord.Embed(
            title=parse_variables(data["title"], member),
            description=parse_variables(data["description"], member),
            color=hex_to_color(data.get("color", "#3498db")),
        )
        return embed

    # ================= EVENTS =================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            db = load_db()
            gid = str(member.guild.id)
            data = db.get(gid)

            if not data or not data.get("enabled"):
                return

            now = datetime.utcnow().timestamp()
            if now - data.get("last_join", 0) < data.get("cooldown", 0):
                return

            data["last_join"] = now
            save_db(db)

            await asyncio.sleep(data.get("delay", 0))

            profile = data.get("greet")
            channel_id = data.get("channel")

            if profile and channel_id:
                embed_data = data["embeds"].get(profile)
                if embed_data:
                    channel = member.guild.get_channel(channel_id)
                    if channel:
                        embed = self.build_embed(embed_data, member)
                        await channel.send(embed=embed)

            if data.get("dm_greet"):
                if profile:
                    embed_data = data["embeds"].get(profile)
                    if embed_data:
                        embed = self.build_embed(embed_data, member)
                        await member.send(embed=embed)

        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            db = load_db()
            gid = str(member.guild.id)
            data = db.get(gid)

            if not data or not data.get("enabled"):
                return

            profile = data.get("leave")
            channel_id = data.get("channel")

            if profile and channel_id:
                embed_data = data["embeds"].get(profile)
                if embed_data:
                    channel = member.guild.get_channel(channel_id)
                    if channel:
                        embed = self.build_embed(embed_data, member)
                        await channel.send(embed=embed)

        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(EditV2(bot))
