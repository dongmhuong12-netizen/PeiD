import discord
from core.embed_storage import save_embed, embed_exists


class EmbedView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.message = None

        self.embed_data = {
            "title": "New Embed",
            "description": "Edit using buttons below.",
            "color": 0x5865F2,
            "image": None
        }

        self.saved_name = None


    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author_id


    def build_embed(self):
        embed = discord.Embed(
            title=self.embed_data["title"],
            description=self.embed_data["description"],
            color=self.embed_data["color"]
        )

        if self.embed_data["image"]:
            embed.set_image(url=self.embed_data["image"])

        return embed


    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.saved_name:
            await interaction.response.send_message(
                "❌ Bạn chưa đặt tên embed.",
                ephemeral=True
            )
            return

        # 🔒 CHỐNG TRÙNG
        if embed_exists(self.saved_name):
            await interaction.response.send_message(
                "❌ Tên embed này đã tồn tại. Ai save trước thì sống.",
                ephemeral=True
            )
            return

        save_embed(self.saved_name, self.embed_data)

        await interaction.response.send_message(
            f"✅ Embed `{self.saved_name}` saved.",
            ephemeral=True
        )


    async def on_timeout(self):
        # ⚠️ Chỉ cảnh báo nếu chưa Save
        if not self.saved_name:
            try:
                await self.message.channel.send(
                    "⚠️ Bạn vừa xoá một embed chưa Save. Nó được coi như chưa từng tồn tại."
                )
            except:
                pass
