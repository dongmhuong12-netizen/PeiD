import discord

# =========================================
# UTIL
# =========================================

def hex_to_color(hex_code: str) -> discord.Color:
    hex_code = hex_code.replace("#", "")
    return discord.Color(int(hex_code, 16))


# =========================================
# MODALS
# =========================================

class EditTextModal(discord.ui.Modal):

    def __init__(self, field_name: str, current_value: str = ""):
        super().__init__(title=f"Set {field_name}")
        self.field_name = field_name

        self.input = discord.ui.TextInput(
            label=field_name,
            default=current_value,
            style=discord.TextStyle.paragraph if field_name == "Description" else discord.TextStyle.short,
            required=False,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        view: EmbedManagerView = self.view
        key = self.field_name.lower()

        view.embed_data[key] = self.input.value
        view.dirty = True

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )


class SetImageModal(discord.ui.Modal):

    def __init__(self, field: str):
        super().__init__(title=f"Set {field}")
        self.field = field

        self.url = discord.ui.TextInput(
            label="Image URL",
            placeholder="https://example.com/image.gif",
            required=False,
            max_length=500
        )

        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        view: EmbedManagerView = self.view
        view.embed_data[self.field] = self.url.value
        view.dirty = True

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )


class SetColorModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(title="Set Embed Color")

        self.hex_input = discord.ui.TextInput(
            label="HEX Color",
            placeholder="#5865F2",
            required=True,
            max_length=7
        )

        self.add_item(self.hex_input)

    async def on_submit(self, interaction: discord.Interaction):
        view: EmbedManagerView = self.view

        try:
            view.embed_data["color"] = self.hex_input.value
            view.dirty = True
        except:
            await interaction.response.send_message("Invalid HEX.", ephemeral=True)
            return

        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view
        )


class ConfirmDeleteModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(title="Confirm Delete")

        self.confirm = discord.ui.TextInput(
            label="Type DELETE to confirm",
            required=True
        )

        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        view: EmbedManagerView = self.view

        if self.confirm.value != "DELETE":
            await interaction.response.send_message("❌ Wrong confirmation.", ephemeral=True)
            return

        view.delete_callback(view.embed_name)

        await interaction.response.edit_message(
            content="🗑 Embed deleted permanently.",
            embed=None,
            view=None
        )


# =========================================
# MAIN VIEW
# =========================================

class EmbedManagerView(discord.ui.View):

    def __init__(self, embed_name, embed_data, save_callback, delete_callback):
        super().__init__(timeout=None)

        self.embed_name = embed_name
        self.embed_data = embed_data
        self.save_callback = save_callback
        self.delete_callback = delete_callback

        self.dirty = False
        self.closed = False

    # =========================================
    # BUILD EMBED
    # =========================================

    def build_embed(self):

        color = discord.Color.blurple()
        if self.embed_data.get("color"):
            try:
                color = hex_to_color(self.embed_data["color"])
            except:
                pass

        embed = discord.Embed(
            title=self.embed_data.get("title", "No Title"),
            description=self.embed_data.get("description", "No Description"),
            color=color
        )

        if self.embed_data.get("image"):
            embed.set_image(url=self.embed_data["image"])

        if self.embed_data.get("thumbnail"):
            embed.set_thumbnail(url=self.embed_data["thumbnail"])

        return embed

    # =========================================
    # BUTTONS
    # =========================================

    @discord.ui.button(label="Title", style=discord.ButtonStyle.secondary, row=0)
    async def edit_title(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(
            EditTextModal("Title", self.embed_data.get("title", ""))
        )

    @discord.ui.button(label="Description", style=discord.ButtonStyle.secondary, row=0)
    async def edit_desc(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(
            EditTextModal("Description", self.embed_data.get("description", ""))
        )

    @discord.ui.button(label="Color", style=discord.ButtonStyle.secondary, row=0)
    async def edit_color(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(SetColorModal())

    @discord.ui.button(label="Image", style=discord.ButtonStyle.secondary, row=1)
    async def edit_image(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(SetImageModal("image"))

    @discord.ui.button(label="Thumbnail", style=discord.ButtonStyle.secondary, row=1)
    async def edit_thumbnail(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(SetImageModal("thumbnail"))

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, row=2)
    async def save(self, interaction: discord.Interaction, button):
        self.save_callback(self.embed_name, self.embed_data)
        self.dirty = False
        await interaction.response.send_message("💾 Saved.", ephemeral=True)

    @discord.ui.button(label="Send", style=discord.ButtonStyle.primary, row=2)
    async def send(self, interaction: discord.Interaction, button):

        if self.dirty:
            await interaction.response.send_message(
                "⚠ You have unsaved changes.",
                ephemeral=True
            )
            return

        await interaction.channel.send(embed=self.build_embed())
        await interaction.response.send_message("📤 Sent.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, row=3)
    async def close(self, interaction: discord.Interaction, button):

        self.closed = True

        for item in self.children:
            item.disabled = True

        open_btn = OpenButton()
        self.add_item(open_btn)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, row=3)
    async def delete(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(ConfirmDeleteModal())


class OpenButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Open", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interation):
        view: EmbedManagerView = self.view
        view.closed = False

        view.remove_item(self)

        for item in view.children:
            item.disabled = False

        await interaction.response.edit_message(view=view)
