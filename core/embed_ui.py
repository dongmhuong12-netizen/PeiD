import discord
import json
import os

from core.embed_storage import save_embed, delete_embed
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"
ACTIVE_EMBED_VIEWS = {}


# =========================
# REACTION STORAGE
# =========================

def load_reaction_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# EDIT MODALS
# =========================

class EditTitleModal(discord.ui.Modal, title="Edit Title"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.input = discord.ui.TextInput(label="New Title", required=False)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["title"] = self.input.value
        await self.view.update_message(interaction)


class EditDescriptionModal(discord.ui.Modal, title="Edit Description"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.input = discord.ui.TextInput(
            label="New Description",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["description"] = self.input.value
        await self.view.update_message(interaction)


class EditColorModal(discord.ui.Modal, title="Edit Color (HEX)"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.input = discord.ui.TextInput(
            label="Hex Color (vd: FF0000)",
            required=True
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.view.data["color"] = int(self.input.value.replace("#", ""), 16)
            await self.view.update_message(interaction)
        except ValueError:
            await interaction.response.send_message("Hex không hợp lệ.", ephemeral=True)


class EditImageModal(discord.ui.Modal, title="Set Image URL"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.input = discord.ui.TextInput(label="Image URL", required=False)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["image"] = self.input.value
        await self.view.update_message(interaction)


# =========================
# REACTION ROLE MODAL (FIXED PROPERLY)
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis = discord.ui.TextInput(label="Emojis (😀, 😎)", required=True)
        self.roles = discord.ui.TextInput(label="Role IDs (123,456)", required=True)
        self.mode = discord.ui.TextInput(label="Mode (single/multi)", default="single")

        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        emojis = [e.strip() for e in self.emojis.value.split(",") if e.strip()]
        roles = [r.strip() for r in self.roles.value.split(",") if r.strip()]
        mode = self.mode.value.lower().strip()

        if len(emojis) != len(roles):
            await interaction.response.send_message("Emoji và role không khớp.", ephemeral=True)
            return

        if mode not in ["single", "multi"]:
            await interaction.response.send_message("Mode phải là single hoặc multi.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        data = load_reaction_data()

        key = f"{guild_id}::embed::{self.view.name}"

        new_group = {
            "mode": mode,
            "emojis": emojis,
            "roles": roles
        }

        # 🔥 FIX THẬT SỰ: append group thay vì overwrite
        if key not in data:
            data[key] = {
                "guild_id": guild_id,
                "embed_name": self.view.name,
                "groups": []
            }

        data[key]["groups"].append(new_group)

        save_reaction_data(data)

        await interaction.response.send_message("Reaction role đã lưu.", ephemeral=True)


# =========================
# EMBED VIEW
# =========================

class EmbedUIView(discord.ui.View):

    def __init__(self, name: str, data: dict):
        super().__init__(timeout=None)
        self.name = name
        self.data = data
        self.message = None

        if name not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[name] = []

        ACTIVE_EMBED_VIEWS[name].append(self)

    def build_embed(self):
        data = self.data

        if hasattr(self, "guild") and hasattr(self, "member"):
            data = apply_variables(data, self.guild, self.member)

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color", 0x5865F2)
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        return embed

    async def update_message(self, interaction: discord.Interaction):
        self.guild = interaction.guild
        self.member = interaction.user

        embed = self.build_embed()

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    # ===== EDIT BUTTONS =====

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.secondary)
    async def edit_title(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary)
    async def set_image(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditColorModal(self))

    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.secondary)
    async def reaction_roles(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))

    # ===== SAVE / DELETE =====

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.secondary)
    async def save_btn(self, interaction: discord.Interaction, button):
        save_embed(interaction.guild.id, self.name, self.data)
        await interaction.response.send_message("Embed đã lưu.", ephemeral=True)

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.secondary)
    async def delete_btn(self, interaction: discord.Interaction, button):
        delete_embed(interaction.guild.id, self.name)

        if self.name in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[self.name].remove(self)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
