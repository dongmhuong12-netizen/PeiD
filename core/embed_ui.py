import discord
import json
import os

from core.embed_storage import save_embed, delete_embed

DATA_FILE = "data/reaction_roles.json"

ACTIVE_EMBED_VIEWS = {}


# =========================
# REACTION ROLE STORAGE
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
# REACTION ROLE MODAL
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):

    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis_input = discord.ui.TextInput(
            label="Emojis (😀, 😎, 🔥)",
            required=True
        )

        self.roles_input = discord.ui.TextInput(
            label="Role IDs (123, 456, 789)",
            required=True
        )

        self.mode_input = discord.ui.TextInput(
            label="Mode (single / multi)",
            default="single",
            required=True
        )

        self.add_item(self.emojis_input)
        self.add_item(self.roles_input)
        self.add_item(self.mode_input)

    async def on_submit(self, interaction: discord.Interaction):

        emojis = [e.strip() for e in self.emojis_input.value.split(",")]
        roles = [r.strip() for r in self.roles_input.value.split(",")]
        mode = self.mode_input.value.lower().strip()

        if len(emojis) != len(roles):
            await interaction.response.send_message(
                "❌ Emoji và role không khớp.",
                ephemeral=True
            )
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

        await interaction.response.send_message(
            "✅ Reaction role đã lưu.",
            ephemeral=True
        )


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
            title=self.data.get("title", ""),
            description=self.data.get("description", ""),
            color=self.data.get("color", 0x5865F2)
        )

        if self.data.get("image"):
            embed.set_image(url=self.data["image"])

        return embed

    # ===== REACTION ROLE BUTTON =====
    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.success)
    async def reaction_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReactionRoleModal(self))

    # ===== SAVE BUTTON =====
    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.primary)
    async def save_embed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_embed(self.name, self.data)
        await interaction.response.send_message("💾 Embed đã lưu.", ephemeral=True)

    # ===== DELETE BUTTON =====
    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_embed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        delete_embed(self.name)
        await interaction.response.send_message("🗑 Embed đã xoá.", ephemeral=True)
