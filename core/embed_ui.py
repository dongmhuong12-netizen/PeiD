import discord
from core.embed_storage import save_embed, load_embed, delete_embed

# =============================
# GLOBAL REGISTRY
# =============================

ACTIVE_EMBED_VIEWS: dict[str, list["EmbedBuilderView"]] = {}


# =============================
# MODALS
# =============================

class TitleModal(discord.ui.Modal, title="Edit Title"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.title_input = discord.ui.TextInput(label="Title", required=True)
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
        self.image_input = discord.ui.TextInput(label="Image URL", required=True)
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["image"] = self.image_input.value
        await self.view.update_embed(interaction)


class ColorModal(discord.ui.Modal, title="Set Embed Color"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.color_input = discord.ui.TextInput(
            label="Hex Color (#ff0000)",
            required=True
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

    def __init__(self, name: str, existing_data: dict | None = None):
        super().__init__(timeout=600)

        self.name = name
        self.message = None
        self.saved = False

        if existing_data:
            self.embed_data = existing_data
        else:
            self.embed_data = {
                "title": "New Embed",
                "description": "Edit using buttons below.",
                "color": discord.Color.blurple().value,
                "image": None
            }

        # 🔥 Đăng ký vào registry
        if name not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[name] = []

        ACTIVE_EMBED_VIEWS[name].append(self)

    # =============================
    # CLEANUP
    # =============================

    async def close_all_same_name(self):
        if self.name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[self.name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[self.name] = []

    async def unregister(self):
        if self.name in ACTIVE_EMBED_VIEWS:
            if self in ACTIVE_EMBED_VIEWS[self.name]:
                ACTIVE_EMBED_VIEWS[self.name].remove(self)

    async def on_timeout(self):
        await self.unregister()
        try:
            if self.message:
                await self.message.delete()
        except:
            pass

    # =============================
    # BUILD
    # =============================

    def build_embed(self):
        embed = discord.Embed(
            title=self.embed_data.get("title"),
            description=self.embed_data.get("description"),
            color=self.embed_data.get("color")
        )

        if self.embed_data.get("image"):
            embed.set_image(url=self.embed_data["image"])

        return embed

    async def update_embed(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    # =============================
    # BUTTONS
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

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_embed(self.name, self.embed_data)
        self.saved = True

        await interaction.response.send_message(
            f"✅ Embed `{self.name}` saved.",
            ephemeral=True
        )

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.red)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        delete_embed(self.name)

        # 🔥 Xoá toàn bộ UI cùng tên
        await self.close_all_same_name()

        await interaction.response.send_message(
            f"🗑 Embed `{self.name}` UI deleted everywhere.",
            ephemeral=True
        )
