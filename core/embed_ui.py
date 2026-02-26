import discord
from core.embed_storage import save_embed, embed_exists


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


    # =============================
    # SAVE BUTTON
    # =============================
    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 🔒 CHỐNG TRÙNG TUYỆT ĐỐI
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
    # TIMEOUT (CHƯA SAVE → CẢNH BÁO)
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
