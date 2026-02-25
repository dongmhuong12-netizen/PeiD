import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import json
import asyncio
import re

DB_PATH = "database.db"

active_sessions = {}
session_locks = {}

HEX_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{6})$")


# =========================
# DATABASE
# =========================

def get_profile(guild_id: int, name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM embeds WHERE guild_id = ? AND name = ?",
            (guild_id, name),
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def save_profile(guild_id: int, name: str, data: dict):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE embeds SET data = ? WHERE guild_id = ? AND name = ?",
            (json.dumps(data), guild_id, name),
        )
        conn.commit()


# =========================
# UTIL
# =========================

def safe_color(hex_color: str):
    if not hex_color:
        return discord.Color.blurple()

    if HEX_PATTERN.match(hex_color):
        return discord.Color(int(hex_color[1:], 16))

    return discord.Color.blurple()


def apply_variables(text: str, interaction: discord.Interaction):
    if not text:
        return text

    return (
        text.replace("{user}", interaction.user.name)
        .replace("{mention}", interaction.user.mention)
        .replace("{server}", interaction.guild.name)
        .replace("{membercount}", str(interaction.guild.member_count))
    )


# =========================
# FIELD SELECT
# =========================

class FieldSelect(discord.ui.Select):
    def __init__(self, view):
        options = []
        for i, field in enumerate(view.data.get("fields", [])):
            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {field['name'][:80]}",
                    value=str(i)
                )
            )

        super().__init__(placeholder="Manage Field...", options=options)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        await interaction.response.send_modal(EditFieldModal(self.view_ref, index))


# =========================
# MAIN VIEW
# =========================

class EmbedBuilder(discord.ui.View):

    def __init__(self, bot, guild_id, profile_name, data):
        super().__init__(timeout=1800)
        self.bot = bot
        self.guild_id = guild_id
        self.profile_name = profile_name
        self.data = data or {}

        if self.data.get("fields"):
            self.add_item(FieldSelect(self))

    async def on_timeout(self):
        key = (self.guild_id, self.profile_name)
        active_sessions.pop(key, None)

    def build(self, interaction=None):
        embed = discord.Embed(
            title=apply_variables(self.data.get("title"), interaction) if interaction else self.data.get("title"),
            description=apply_variables(self.data.get("description"), interaction) if interaction else self.data.get("description"),
            color=safe_color(self.data.get("color"))
        )

        if self.data.get("thumbnail"):
            embed.set_thumbnail(url=self.data["thumbnail"])

        if self.data.get("image"):
            embed.set_image(url=self.data["image"])

        if self.data.get("footer"):
            embed.set_footer(text=self.data["footer"])

        if self.data.get("author"):
            embed.set_author(name=self.data["author"])

        for field in self.data.get("fields", [])[:25]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )

        return embed

    async def refresh(self, interaction):
        self.clear_items()
        if self.data.get("fields"):
            self.add_item(FieldSelect(self))
        self.add_buttons()
        await interaction.response.edit_message(embed=self.build(interaction), view=self)

    def add_buttons(self):
        self.add_item(EditButton("Title", "title"))
        self.add_item(EditButton("Description", "description", paragraph=True))
        self.add_item(EditButton("Color (#FFFFFF)", "color"))
        self.add_item(AddFieldButton())
        self.add_item(ClearButton())
        self.add_item(SaveButton())

    # dynamic buttons setup
    def setup_buttons(self):
        self.add_buttons()


# =========================
# BUTTONS
# =========================

class EditButton(discord.ui.Button):
    def __init__(self, label, key, paragraph=False):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.key = key
        self.paragraph = paragraph

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TextModal(self.view, self.key, self.label, self.paragraph))


class AddFieldButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Add Field", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        if len(self.view.data.get("fields", [])) >= 25:
            await interaction.response.send_message("❌ Max 25 fields.", ephemeral=True)
            return
        await interaction.response.send_modal(AddFieldModal(self.view))


class ClearButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Clear All", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        self.view.data = {}
        await self.view.refresh(interaction)


class SaveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Save", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        save_profile(self.view.guild_id, self.view.profile_name, self.view.data)
        await interaction.response.send_message("✅ Saved.", ephemeral=True)


# =========================
# MODALS
# =========================

class TextModal(discord.ui.Modal):
    def __init__(self, view, key, title, paragraph=False):
        super().__init__(title=title)
        self.view_ref = view
        self.key = key

        style = discord.TextStyle.paragraph if paragraph else discord.TextStyle.short

        self.input = discord.ui.TextInput(label=title, style=style, required=False)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view_ref.data[self.key] = str(self.input)
        await self.view_ref.refresh(interaction)


class AddFieldModal(discord.ui.Modal, title="Add Field"):
    name = discord.ui.TextInput(label="Field Name", max_length=256)
    value = discord.ui.TextInput(label="Field Value", style=discord.TextStyle.paragraph, max_length=1024)

    def __init__(self, view):
        super().__init__()
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view_ref.data.setdefault("fields", []).append({
            "name": str(self.name),
            "value": str(self.value),
            "inline": False
        })
        await self.view_ref.refresh(interaction)


class EditFieldModal(discord.ui.Modal):
    def __init__(self, view, index):
        super().__init__(title="Edit Field")
        self.view_ref = view
        self.index = index

        field = view.data["fields"][index]

        self.name_input = discord.ui.TextInput(label="Name", default=field["name"])
        self.value_input = discord.ui.TextInput(label="Value", style=discord.TextStyle.paragraph, default=field["value"])
        self.inline_input = discord.ui.TextInput(label="Inline (true/false)", default=str(field.get("inline", False)))

        self.add_item(self.name_input)
        self.add_item(self.value_input)
        self.add_item(self.inline_input)

    async def on_submit(self, interaction: discord.Interaction):
        inline = self.inline_input.value.lower() == "true"

        self.view_ref.data["fields"][self.index] = {
            "name": str(self.name_input),
            "value": str(self.value_input),
            "inline": inline
        }

        await self.view_ref.refresh(interaction)


# =========================
# COG
# =========================

class EditV2(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed_edit_show", description="Open embed editor")
    async def embed_edit_show(self, interaction: discord.Interaction, name: str):

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Need Manage Guild.", ephemeral=True)
            return

        key = (interaction.guild.id, name)

        if key not in session_locks:
            session_locks[key] = asyncio.Lock()

        async with session_locks[key]:

            profile = get_profile(interaction.guild.id, name)

            if not profile:
                await interaction.response.send_message("❌ Profile not found.", ephemeral=True)
                return

            if key in active_sessions:
                try:
                    old_msg = await interaction.channel.fetch_message(active_sessions[key])
                    await old_msg.delete()
                except:
                    pass

            view = EmbedBuilder(self.bot, interaction.guild.id, name, profile)
            view.setup_buttons()

            await interaction.response.send_message(embed=view.build(interaction), view=view)
            msg = await interaction.original_response()
            active_sessions[key] = msg.id


async def setup(bot: commands.Bot):
    await bot.add_cog(EditV2(bot))
