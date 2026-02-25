import discord
from core.embed_storage import save_embed


class TitleModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Edit Title")

        self.title_input = discord.ui.TextInput(
            label="Title",
            max_length=256
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.title = self.title_input.value
        await interaction.response.edit_message(embed=embed)


class DescriptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Edit Description")

        self.desc_input = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            max_length=4000
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.description = self.desc_input.value
        await interaction.response.edit_message(embed=embed)


class ColorModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Edit Color (HEX)")

        self.color_input = discord.ui.TextInput(
            label="HEX Color",
            placeholder="#5865F2"
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]

        try:
            embed.color = int(self.color_input.value.replace("#", ""), 16)
        except:
            await interaction.response.send_message(
                "❌ Invalid HEX color.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(embed=embed)


class ImageModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Set Image URL")

        self.image_input = discord.ui.TextInput(
            label="Image URL (gif supported)"
        )
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.set_image(url=self.image_input.value)
        await interaction.response.edit_message(embed=embed)


class EmbedBuilderView(discord.ui.View):
    def __init__(self, embed_name: str):
        super().__init__(timeout=None)
        self.embed_name = embed_name

    @discord.ui.button(label="Title", style=discord.ButtonStyle.primary)
    async def edit_title(self, interaction, button):
        await interaction.response.send_modal(TitleModal())

    @discord.ui.button(label="Description", style=discord.ButtonStyle.secondary)
    async def edit_desc(self, interaction, button):
        await interaction.response.send_modal(DescriptionModal())

    @discord.ui.button(label="Color", style=discord.ButtonStyle.success)
    async def edit_color(self, interaction, button):
        await interaction.response.send_modal(ColorModal())

    @discord.ui.button(label="Image", style=discord.ButtonStyle.secondary)
    async def edit_image(self, interaction, button):
        await interaction.response.send_modal(ImageModal())

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save_button(self, interaction, button):
        embed = interaction.message.embeds[0]

        data = {
            "title": embed.title,
            "description": embed.description,
            "color": embed.color.value if embed.color else None,
            "image": embed.image.url if embed.image else None
        }

        save_embed(self.embed_name, data)

        await interaction.response.send_message(
            f"✅ Embed `{self.embed_name}` saved.",
            ephemeral=True
        )
