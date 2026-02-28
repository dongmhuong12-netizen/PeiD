import discord
import json
import os

from core.embed_storage import save_embed, delete_embed

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
        except:
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
# REACTION ROLE MODAL
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
        emojis = [e.strip() for e in self.emojis.value.split(",")]
        roles = [r.strip() for r in self.roles.value.split(",")]
        mode = self.mode.value.lower().strip()

        if len(emojis) != len(roles):
            await interaction.response.send_message("Emoji và role không khớp.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        data = load_reaction_data()

        key = f"{guild_id}::embed::{self.view.name}"

        config = data.get(key, {
            "guild_id": guild_id,
            "embed_name": self.view.name,
            "groups": []
        })

        config["groups"].append({
            "mode": mode,
            "emojis": emojis,
            "roles": roles
        })

        data[key] = config
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

        ACTIVE_EMBED_VIEWS.setdefault(name, []).append(self)

    def build_embed(self):
        embed = discord.Embed(
            title=self.data.get("title"),
            description=self.data.get("description"),
            color=self.data.get("color", 0x5865F2)
        )

        if self.data.get("image"):
            embed.set_image(url=self.data["image"])

        return embed

    async def update_message(self, interaction):
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    # ===== EDIT BUTTONS =====

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.secondary)
    async def edit_title(self, interaction, button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction, button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary)
    async def set_image(self, interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction, button):
        await interaction.response.send_modal(EditColorModal(self))

    # ===== REACTION =====

    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.success)
    async def reaction_roles(self, interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))

    # ===== SAVE / DELETE =====

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.primary)
    async def save_btn(self, interaction, button):
        save_embed(self.name, self.data)
        await interaction.response.send_message("Embed đã lưu.", ephemeral=True)

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction, button):
        delete_embed(self.name)
        await interaction.response.send_message("Embed đã xoá.", ephemeral=True)
