import discord
from core.embed_storage import save_embed, load_embed


# =============================
# MODALS
# =============================

class TitleModal(discord.ui.Modal, title="Edit Title"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.title_input = discord.ui.TextInput(
            label="Title",
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

        # ✅ FIX ghi nhớ data
        if existing_data:
            self.embed_data = existing_data
        else:
            self.embed_data = {
                "title": "New Embed",
                "description": "Edit using buttons below.",
                "color": discord.Color.blurple().value,
                "image": None
            }

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

    # =============================
    # SAVE (FIX SONG SONG)
    # =============================

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        old_data = load_embed(self.name)

        # 🔥 Nếu đã tồn tại → xóa embed cũ trước
        if old_data and "channel_id" in old_data and "message_id" in old_data:
            try:
                old_channel = interaction.client.get_channel(old_data["channel_id"])
                if old_channel:
                    old_msg = await old_channel.fetch_message(old_data["message_id"])
                    await old_msg.delete()
            except:
                pass

        # Gửi embed mới
        embed = self.build_embed()
        sent_msg = await interaction.channel.send(embed=embed)

        # Lưu message id + channel id
        self.embed_data["channel_id"] = interaction.channel.id
        self.embed_data["message_id"] = sent_msg.id

        save_embed(self.name, self.embed_data)
        self.saved = True

        await interaction.response.send_message(
            f"✅ Embed `{self.name}` saved & synced.",
            ephemeral=True
        )

    # =============================
    # DELETE
    # =============================

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.red)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_embed(self.name)

        if not data:
            await interaction.response.send_message(
                "⚠ Embed này chưa từng được lưu.",
                ephemeral=True
            )
            return

        if "channel_id" in data and "message_id" in data:
            try:
                ch = interaction.client.get_channel(data["channel_id"])
                if ch:
                    msg = await ch.fetch_message(data["message_id"])
                    await msg.delete()
            except:
                pass

        save_embed(self.name, None)

        await interaction.response.send_message(
            f"🗑 Embed `{self.name}` deleted completely.",
            ephemeral=True
        )

    # =============================
    # TIMEOUT
    # =============================

    async def on_timeout(self):
        if not self.saved and self.message:
            try:
                await self.message.channel.send(
                    "⚠️ Embed chưa được save đã biến mất."
                )
            except:
                pass
