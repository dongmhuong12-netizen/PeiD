import discord
from discord.ui import View, Modal, TextInput
from .embed_storage import save_embed, delete_embed


# =============================
# EMBED UI VIEW
# =============================

class EmbedUIView(View):
    def __init__(self, name: str, embed_data: dict):
        super().__init__(timeout=None)
        self.name = name
        self.embed_data = embed_data
        self.saved = False

    # =============================
    # BUILD EMBED
    # =============================

    def build_embed(self):
        embed = discord.Embed(
            title=self.embed_data.get("title"),
            description=self.embed_data.get("description"),
            color=self.embed_data.get("color", 0x2F3136)
        )

        if self.embed_data.get("image"):
            embed.set_image(url=self.embed_data["image"])

        return embed

    # =============================
    # BUTTONS (ALL GRAY STYLE)
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
        await interaction.message.delete()

        await interaction.response.send_message(
            f"Embed `{self.name}` đã được xoá vĩnh viễn, có thể tạo embed mới bằng tên của embed này.",
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
            embed=self.view.build_embed(),
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
            embed=self.view.build_embed(),
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
            embed=self.view.build_embed(),
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
            embed=self.view.build_embed(),
            view=self.view
        )
