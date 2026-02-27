import discord
from discord.ui import View, Modal, TextInput
import re
from .embed_storage import save_embed, delete_embed
from .variable_engine import apply_variables   # ✅ THÊM


# =============================
# GLOBAL ACTIVE VIEWS
# =============================

ACTIVE_EMBED_VIEWS = {}


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

    # =============================
    # FIXED LINK TOKEN PARSER
    # =============================

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

    # =============================
    # BUILD EMBED
    # =============================

    def build_embed(self, interaction: discord.Interaction = None):
        color_value = self.embed_data.get("color")
        if color_value is None:
            color_value = 0x2F3136

        embed_data = self.embed_data.copy()

        # =============================
        # ✅ APPLY VARIABLE ENGINE (PREVIEW)
        # =============================
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

        # ===== EXTRACT LINK TOKEN =====
        if isinstance(description, str):
            description, link_label, link_url = self.extract_link_tokens(description)

        # ===== CLEAN TEXT =====
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

        # ===== BUILD VIEW =====
        self.clear_items()
        self._add_default_buttons()

        if link_label and link_url:
            self.add_item(discord.ui.Button(label=link_label, url=link_url))

        return embed

    # =============================
    # DEFAULT BUTTONS
    # =============================

    def _add_default_buttons(self):
        self.add_item(self.edit_title)
        self.add_item(self.edit_description)
        self.add_item(self.set_image)
        self.add_item(self.edit_color)
        self.add_item(self.save_button)
        self.add_item(self.delete_button)

    # =============================
    # BUTTONS
    # =============================

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
