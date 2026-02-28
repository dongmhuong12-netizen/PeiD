import discord
from discord.ui import View, Modal, TextInput
import re
import json
import os
from .embed_storage import save_embed, delete_embed
from .variable_engine import apply_variables


# =============================
# GLOBAL ACTIVE VIEWS
# =============================

ACTIVE_EMBED_VIEWS = {}

REACTION_FILE = "data/reaction_roles.json"


def load_reaction_data():
    if not os.path.exists(REACTION_FILE):
        return {}
    with open(REACTION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)
    with open(REACTION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =============================
# EMBED UI VIEW
# =============================

class EmbedUIView(View):
    def __init__(self, name: str, embed_data: dict):
        super().__init__(timeout=None)
        self.name = name
        self.embed_data = embed_data
        self.saved = False
        self.message = None

        if name not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[name] = []
        ACTIVE_EMBED_VIEWS[name].append(self)

    def extract_link_tokens(self, text: str):
        if not text:
            return text, None, None

        label_match = re.search(r'link_label\s*"(.*?)"', text, re.IGNORECASE)
        url_match = re.search(r'link_url\s*"(.*?)"', text, re.IGNORECASE)

        label = label_match.group(1).strip() if label_match else None
        url = url_match.group(1).strip() if url_match else None

        text = re.sub(r'link_label\s*".*?"', '', text, flags=re.IGNORECASE)
        text = re.sub(r'link_url\s*".*?"', '', text, flags=re.IGNORECASE)

        return text.strip(), label, url

    def build_embed(self, interaction: discord.Interaction = None):
        color_value = self.embed_data.get("color")
        if color_value is None:
            color_value = 0x2F3136

        embed_data = self.embed_data.copy()

        if interaction:
            embed_data = apply_variables(
                embed_data,
                interaction.guild,
                interaction.user
            )

        title = embed_data.get("title")
        description = embed_data.get("description")

        link_label = None
        link_url = None

        if isinstance(description, str):
            description, link_label, link_url = self.extract_link_tokens(description)

        def clean_text(text):
            if not isinstance(text, str):
                return text
            text = text.replace("\u200b", "")
            text = text.replace("\ufeff", "")
            text = text.replace("\r", "")
            return text.strip()

        title = clean_text(title)
        description = clean_text(description)

        embed = discord.Embed(
            title=title,
            description=description,
            color=color_value
        )

        if embed_data.get("image"):
            embed.set_image(url=embed_data["image"])

        if embed_data.get("thumbnail"):
            embed.set_thumbnail(url=embed_data["thumbnail"])

        self.clear_items()
        self._add_default_buttons()

        if link_label and link_url:
            self.add_item(discord.ui.Button(label=link_label, url=link_url))

        return embed

    def _add_default_buttons(self):
        self.add_item(self.edit_title)
        self.add_item(self.edit_description)
        self.add_item(self.set_image)
        self.add_item(self.edit_color)
        self.add_item(self.save_button)
        self.add_item(self.delete_button)
        self.add_item(self.reaction_roles_button)

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.gray)
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.gray)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.gray)
    async def set_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.gray)
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColorModal(self))

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.gray)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_embed(self.name, self.embed_data)
        self.saved = True

        await interaction.response.send_message(
            f"Embed `{self.name}` đã được lưu.",
            ephemeral=True
        )

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.gray)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        delete_embed(self.name)

        if self.name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[self.name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[self.name] = []

        await interaction.response.send_message(
            f"Embed `{self.name}` đã được xoá vĩnh viễn.",
            ephemeral=True
        )

    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.green)
    async def reaction_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReactionRoleModal(self))


# =============================
# MODALS
# =============================

class TitleModal(Modal, title="Chỉnh sửa tiêu đề"):
    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

        self.title_input = TextInput(
            label="Tiêu đề",
            default=view.embed_data.get("title"),
            required=False
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["title"] = self.title_input.value
        await interaction.response.edit_message(
            embed=self.view.build_embed(interaction),
            view=self.view
        )


class DescriptionModal(Modal, title="Chỉnh sửa mô tả"):
    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

        self.desc_input = TextInput(
            label="Mô tả",
            style=discord.TextStyle.paragraph,
            default=view.embed_data.get("description"),
            required=False
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["description"] = self.desc_input.value
        await interaction.response.edit_message(
            embed=self.view.build_embed(interaction),
            view=self.view
        )


class ImageModal(Modal, title="Đặt ảnh Embed"):
    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

        self.image_input = TextInput(
            label="URL hình ảnh",
            default=view.embed_data.get("image"),
            required=False
        )
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["image"] = self.image_input.value
        await interaction.response.edit_message(
            embed=self.view.build_embed(interaction),
            view=self.view
        )


class ColorModal(Modal, title="Chỉnh sửa màu (Hex)"):
    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

        self.color_input = TextInput(
            label="Mã màu (VD: FF0000)",
            required=False
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_value = int(self.color_input.value, 16)
            self.view.embed_data["color"] = color_value
        except:
            pass

        await interaction.response.edit_message(
            embed=self.view.build_embed(interaction),
            view=self.view
        )


class ReactionRoleModal(Modal, title="Thêm Reaction Role"):

    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

        self.mode_input = TextInput(
            label="Mode (single / multi)",
            required=True
        )

        self.emoji_input = TextInput(
            label="Emoji",
            required=True
        )

        self.role_input = TextInput(
            label="Role ID",
            required=True
        )

        self.add_item(self.mode_input)
        self.add_item(self.emoji_input)
        self.add_item(self.role_input)

    async def on_submit(self, interaction: discord.Interaction):

        mode = self.mode_input.value.lower().strip()
        emoji = self.emoji_input.value.strip()

        try:
            role_id = int(self.role_input.value.strip())
        except:
            await interaction.response.send_message(
                "Role ID không hợp lệ.",
                ephemeral=True
            )
            return

        if mode not in ["single", "multi"]:
            await interaction.response.send_message(
                "Mode phải là 'single' hoặc 'multi'.",
                ephemeral=True
            )
            return

        data = load_reaction_data()

        temp_key = f"embed::{self.view.name}"
        config = data.get(temp_key)

        if not config:
            config = {
                "guild_id": interaction.guild.id,
                "embed_name": self.view.name,
                "groups": []
            }

        target_group = None
        for group in config["groups"]:
            if group["mode"] == mode:
                target_group = group
                break

        if not target_group:
            target_group = {
                "mode": mode,
                "emojis": [],
                "roles": []
            }
            config["groups"].append(target_group)

        target_group["emojis"].append(emoji)
        target_group["roles"].append(role_id)

        data[temp_key] = config
        save_reaction_data(data)

        await interaction.response.send_message(
            f"Đã thêm reaction role ({mode}) vào embed `{self.view.name}`.",
            ephemeral=True
        )
