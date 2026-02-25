import discord


class EmbedEditorView(discord.ui.View):
    def __init__(self, embed_data: dict, manager, guild_id: int, embed_name: str):
        super().__init__(timeout=None)
        self.embed_data = embed_data
        self.manager = manager
        self.guild_id = guild_id
        self.embed_name = embed_name

    def build_embed(self) -> discord.Embed:
        return discord.Embed(
            title=self.embed_data.get("title", "Chưa có tiêu đề"),
            description=self.embed_data.get("description", "Chưa có mô tả"),
            color=self.embed_data.get("color", 0x2F3136)
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Bạn cần quyền Manage Server để chỉnh embed này.",
                ephemeral=True
            )
            return False
        return True

    # ===== ROW 1 =====

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.secondary, row=0)
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary, row=0)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.secondary, row=0)
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditColorModal(self))

    # ===== ROW 2 =====

    @discord.ui.button(label="Send Embed", style=discord.ButtonStyle.secondary, row=1)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(embed=self.build_embed())
        await interaction.response.send_message(
            "Embed đã được gửi.",
            ephemeral=True
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.secondary, row=1)
    async def delete_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Xoá khỏi database
        await self.manager.delete_embed(self.guild_id, self.embed_name)

        # Xoá message editor
        await interaction.message.delete()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, row=1)
    async def close_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)


# ================= MODALS =================


class EditTitleModal(discord.ui.Modal, title="Edit Title"):
    new_title = discord.ui.TextInput(label="New Title", max_length=256)

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["title"] = self.new_title.value

        # Lưu DB
        await self.view.manager.update_embed(
            self.view.guild_id,
            self.view.embed_name,
            self.view.embed_data
        )

        await interaction.response.edit_message(
            embed=self.view.build_embed(),
            view=self.view
        )


class EditDescriptionModal(discord.ui.Modal, title="Edit Description"):
    new_description = discord.ui.TextInput(
        label="New Description",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.embed_data["description"] = self.new_description.value

        await self.view.manager.update_embed(
            self.view.guild_id,
            self.view.embed_name,
            self.view.embed_data
        )

        await interaction.response.edit_message(
            embed=self.view.build_embed(),
            view=self.view
        )


class EditColorModal(discord.ui.Modal, title="Edit Color (HEX)"):
    new_color = discord.ui.TextInput(
        label="HEX Color (example: FF0000)",
        max_length=6
    )

    def __init__(self, view: EmbedEditorView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_value = int(self.new_color.value, 16)
            self.view.embed_data["color"] = color_value

            await self.view.manager.update_embed(
                self.view.guild_id,
                self.view.embed_name,
                self.view.embed_data
            )

            await interaction.response.edit_message(
                embed=self.view.build_embed(),
                view=self.view
            )

        except ValueError:
            await interaction.response.send_message(
                "Invalid HEX color.",
                ephemeral=True
            )
