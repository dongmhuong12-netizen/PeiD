import discord
from core.embed_storage import save_embed, embed_exists, delete_embed


# =============================
# MODALS
# =============================

class TitleModal(discord.ui.Modal, title="Edit Title"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.title_input = discord.ui.TextInput(
            label="Title",
            placeholder="Enter embed title",
            required=True,
            max_length=256
        )

        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["title"] = self.title_input.value
        await self.view.update_embed(interaction)


class DescriptionModal(discord.ui.Modal, title="Edit Description"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.desc_input = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            placeholder="Enter embed description",
            required=True
        )

        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["description"] = self.desc_input.value
        await self.view.update_embed(interaction)


class ImageModal(discord.ui.Modal, title="Set Image URL"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.image_input = discord.ui.TextInput(
            label="Image URL",
            placeholder="https://example.com/image.png",
            required=True
        )

        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["image"] = self.image_input.value
        await self.view.update_embed(interaction)


class ColorModal(discord.ui.Modal, title="Set Embed Color"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.color_input = discord.ui.TextInput(
            label="Hex Color (ví dụ: #ff0000)",
            placeholder="#5865F2",
            required=True,
            max_length=7
        )

        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.color_input.value.strip().replace("#", "")

        try:
            color_int = int(value, 16)
        except ValueError:
            await interaction.response.send_message(
                "❌ Mã màu không hợp lệ.",
                ephemeral=True
            )
            return

        self.view.embed_data["color"] = color_int
        await self.view.update_embed(interaction)


# =============================
# MAIN VIEW
# =============================

class EmbedBuilderView(discord.ui.View):

    def __init__(self, name: str):
        super().__init__(timeout=600)

        self.name = name
        self.message = None
        self.saved = False

        self.embed_data = {
            "title": "New Embed",
            "description": "Edit using buttons below.",
            "color": discord.Color.blurple().value,
            "image": None
        }

    async def interaction_check(self, interaction: discord.Interaction):
        return True

    def build_embed(self):
        embed = discord.Embed(
            title=self.embed_data["title"],
            description=self.embed_data["description"],
            color=self.embed_data["color"]
        )

        if self.embed_data["image"]:
            embed.set_image(url=self.embed_data["image"])

        return embed

    async def update_embed(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    # =============================
    # EDIT BUTTONS
    # =============================

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.blurple)
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.blurple)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.gray)
    async def set_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.gray)
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColorModal(self))

    # =============================
    # SAVE BUTTON
    # =============================

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if embed_exists(self.name):
            await interaction.response.send_message(
                "❌ Embed này đã tồn tại. Ai save trước thì sống.",
                ephemeral=True
            )
            return

        save_embed(self.name, self.embed_data)
        self.saved = True

        await interaction.response.send_message(
            f"✅ Embed `{self.name}` saved.",
            ephemeral=True
        )

    # =============================
    # DELETE BUTTON
    # =============================

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.red)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not embed_exists(self.name):
            await interaction.response.send_message(
                "⚠ Embed này chưa từng được lưu.\n"
                "Nó được coi như chưa từng tồn tại.",
                ephemeral=True
            )
            return

        delete_embed(self.name)

        await interaction.response.send_message(
            f"🗑 Embed `{self.name}` deleted completely.",
            ephemeral=True
        )

        # Disable toàn bộ button sau khi xóa
        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)

    # =============================
    # TIMEOUT
    # =============================

    async def on_timeout(self):

        if not self.saved:
            try:
                if self.message:
                    await self.message.channel.send(
                        "⚠️ Một embed chưa được save đã biến mất.\n"
                        "Nó được coi như chưa từng tồn tại."
                    )
            except:
                pass
