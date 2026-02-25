import discord


class EmbedEditorView(discord.ui.View):
    def __init__(self, embed_data: dict):
        super().__init__(timeout=None)
        self.embed_data = embed_data

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.embed_data.get("title", "Chưa có tiêu đề"),
            description=self.embed_data.get("description", "Chưa có mô tả"),
            color=self.embed_data.get("color", 0x2F3136)
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Bạn cần quyền Manage Server để chỉnh embed này.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✏ Edit Title", style=discord.ButtonStyle.primary)
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTitleModal(self))


class EditTitleModal(discord.ui.Modal, title="Chỉnh sửa tiêu đề"):
    new_title = discord.ui.TextInput(
        label="Tiêu đề mới",
        max_length=256
    )

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["title"] = self.new_title.value

        await interaction.response.edit_message(
            embed=self.view.build_embed(),
            view=self.view
        )
