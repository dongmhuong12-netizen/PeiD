import discord
import json
import os

DATA_FILE = "data/reaction_roles.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):

    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis_input = discord.ui.TextInput(
            label="Emojis (vd: 😀, 😎, 🔥)",
            required=True
        )

        self.roles_input = discord.ui.TextInput(
            label="Role IDs (vd: 123, 456, 789)",
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
                "❌ Số emoji và role ID không khớp.",
                ephemeral=True
            )
            return

        if mode not in ["single", "multi"]:
            await interaction.response.send_message(
                "❌ Mode phải là 'single' hoặc 'multi'.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        data = load_data()

        # 🔥 KEY MỚI CÓ guild_id
        temp_key = f"{guild_id}::embed::{self.view.name}"

        config = data.get(temp_key)

        if not config:
            config = {
                "guild_id": guild_id,
                "embed_name": self.view.name,
                "groups": []
            }

        group = {
            "mode": mode,
            "emojis": emojis,
            "roles": roles
        }

        config["groups"].append(group)

        data[temp_key] = config
        save_data(data)

        await interaction.response.send_message(
            "✅ Reaction role đã được lưu.",
            ephemeral=True
        )
