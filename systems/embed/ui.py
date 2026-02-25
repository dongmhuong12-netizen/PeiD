import discord
from discord.ui import View, Button
from typing import Dict, Any


class EmbedManagerView(View):
    def __init__(self, bot, manager, guild_id: int, embed_name: str):
        super().__init__(timeout=None)

        self.bot = bot
        self.manager = manager
        self.guild_id = guild_id
        self.embed_name = embed_name

        self.embed_data: Dict[str, Any] = {}
        self.is_dirty = False
        self.is_closed = False

    # ==========================
    # LOAD DATA
    # ==========================

    async def load_data(self):
        data = await self.manager.get_embed(self.guild_id, self.embed_name)
        if data:
            self.embed_data = data

    # ==========================
    # STATUS HEADER
    # ==========================

    def build_manager_embed(self):

        status = "🟢 Saved"

        if self.is_closed:
            status = "🔴 Closed"
        elif self.is_dirty:
            status = "🟡 Unsaved changes"

        embed = discord.Embed(
            title=f"Embed Manager: {self.embed_name}",
            description=f"Status: **{status}**",
            color=0x2b2d31
        )

        embed.add_field(
            name="Info",
            value="Save để lưu cấu hình.\nSend để gửi bản đã lưu.",
            inline=False
        )

        return embed

    # ==========================
    # SAVE
    # ==========================

    @discord.ui.button(label="Save", style=discord.ButtonStyle.secondary)
    async def save_button(self, interaction: discord.Interaction, button: Button):

        await self.manager.save_embed(
            self.guild_id,
            self.embed_name,
            self.embed_data,
        )

        self.is_dirty = False

        await interaction.response.edit_message(
            embed=self.build_manager_embed(),
            view=self
        )

    # ==========================
    # SEND
    # ==========================

    @discord.ui.button(label="Send", style=discord.ButtonStyle.secondary)
    async def send_button(self, interaction: discord.Interaction, button: Button):

        if self.is_dirty:
            await interaction.response.send_message(
                "⚠ Bạn chưa Save thay đổi gần nhất.\nEmbed sẽ gửi theo phiên bản đã lưu.",
                ephemeral=True
            )
        else:
            await interaction.response.defer(ephemeral=True)

        data = await self.manager.get_embed(
            self.guild_id,
            self.embed_name
        )

        if not data:
            await interaction.followup.send(
                "❌ Không tìm thấy embed đã lưu.",
                ephemeral=True
            )
            return

        embed = self.build_preview_embed(data)

        await interaction.channel.send(embed=embed)

    # ==========================
    # DELETE
    # ==========================

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.secondary)
    async def delete_button(self, interaction: discord.Interaction, button: Button):

        await self.manager.delete_embed(
            self.guild_id,
            self.embed_name
        )

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"Embed `{self.embed_name}` đã bị xoá hoàn toàn.",
            embed=None,
            view=self
        )

        self.stop()

    # ==========================
    # CLOSE
    # ==========================

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: Button):

        self.is_closed = True

        for item in self.children:
            item.disabled = True

        self.add_item(OpenButton(self))

        await interaction.response.edit_message(
            embed=self.build_manager_embed(),
            view=self
        )

    # ==========================
    # BUILD PREVIEW
    # ==========================

    def build_preview_embed(self, data: Dict[str, Any]):

        embed = discord.Embed(
            title=data.get("title", "No title"),
            description=data.get("description", "No description"),
            color=data.get("color", 0x2b2d31)
        )

        if data.get("footer"):
            embed.set_footer(text=data["footer"])

        if data.get("thumbnail"):
            embed.set_thumbnail(url=data["thumbnail"])

        if data.get("image"):
            embed.set_image(url=data["image"])

        return embed


# ==============================
# OPEN BUTTON
# ==============================

class OpenButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Open", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):

        self.parent_view.is_closed = False

        for item in self.parent_view.children:
            item.disabled = False

        self.parent_view.remove_item(self)

        await interaction.response.edit_message(
            embed=self.parent_view.build_manager_embed(),
            view=self.parent_view
        )
