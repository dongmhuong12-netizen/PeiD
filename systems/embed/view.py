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

    # ================= TITLE =================

    @discord.ui.button(label="✏ Edit Title", style=discord.ButtonStyle.primary)
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTitleModal(self))

    # ================= DESCRIPTION =================

    @discord.ui.button(label="📝 Edit Description", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    # ================= COLOR =================

    @discord.ui.button(label="🎨 Edit Color", style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditColorModal(self))

    # ================= SEND =================

    @discord.ui.button(label="📤 Send Embed", style=discord.ButtonStyle.success)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(embed=self.build_embed())
        await interaction.response.send_message(
            "Đã gửi embed ra channel.",
            ephemeral=True
        )

    # ================= DELETE =================

    @discord.ui.button(label="🗑 Delete", style=discord.ButtonStyle.danger)
    async def delete_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


# ================= MODALS =================


class EditTitleModal(discord.ui.Modal, title="Chỉnh sửa tiêu đề"):
    new_title = discord.ui.TextInput(label="Tiêu đề mới", max_length=256)

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["title"] = self.new_title.value
        await interaction.response.edit_message(
            embed=self.view.build_embed(),
            view=self.view
        )


class EditDescriptionModal(discord.ui.Modal, title="Chỉnh sửa mô tả"):
    new_description = discord.ui.TextInput(
        label="Mô tả mới",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["description"] = self.new_description.value
        await interaction.response.edit_message(
            embed=self.view.build_embed(),
            view=self.view
        )


class EditColorModal(discord.ui.Modal, title="Chỉnh sửa màu (HEX)"):
    new_color = discord.ui.TextInput(
        label="Nhập mã màu HEX (ví dụ: FF0000)",
        max_length=6
    )

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_value = int(self.new_color.value, 16)
            self.view.embed_data["color"] = color_value

            await interaction.response.edit_message(
                embed=self.view.build_embed(),
                view=self.view
            )
        except ValueError:
            await interaction.response.send_message(
                "Mã màu không hợp lệ.",
                ephemeral=True
            )
