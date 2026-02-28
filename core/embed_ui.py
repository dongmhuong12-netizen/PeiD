import discord
import json
import os

DATA_FILE = "data/reaction_roles.json"


# =========================
# JSON STORAGE
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# EMBED UI
# =========================

class EmbedUIView(discord.ui.View):
    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message

    @discord.ui.button(label="Chỉnh sửa tiêu đề", style=discord.ButtonStyle.primary)
    async def edit_title(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Chỉnh sửa nội dung", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Xoá Embed", style=discord.ButtonStyle.danger)
    async def delete_embed(self, interaction: discord.Interaction, button):
        await self.embed_message.delete()
        self.stop()
        await interaction.response.send_message("Đã xoá embed.", ephemeral=True)


class EditTitleModal(discord.ui.Modal, title="Chỉnh sửa tiêu đề"):
    new_title = discord.ui.TextInput(label="Tiêu đề mới", required=True)

    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.view.embed_message.embeds[0]
        embed.title = self.new_title.value
        await self.view.embed_message.edit(embed=embed)
        await interaction.response.send_message("Đã cập nhật tiêu đề.", ephemeral=True)


class EditDescriptionModal(discord.ui.Modal, title="Chỉnh sửa nội dung"):
    new_description = discord.ui.TextInput(
        label="Nội dung mới",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, view: EmbedUIView):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.view.embed_message.embeds[0]
        embed.description = self.new_description.value
        await self.view.embed_message.edit(embed=embed)
        await interaction.response.send_message("Đã cập nhật nội dung.", ephemeral=True)


# =========================
# REACTION ROLE LISTENER
# =========================

async def handle_reaction_add(payload: discord.RawReactionActionEvent, bot: discord.Client):
    if payload.guild_id is None:
        return

    data = load_data()
    message_id = str(payload.message_id)

    if message_id not in data:
        return

    config = data[message_id]

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member.bot:
        return

    emoji = str(payload.emoji)

    if emoji not in config["roles"]:
        return

    role_id = config["roles"][emoji]
    role = guild.get_role(role_id)

    if config["mode"] == "single":
        # remove other roles first
        for e, r_id in config["roles"].items():
            if e != emoji:
                r = guild.get_role(r_id)
                if r in member.roles:
                    await member.remove_roles(r)

    await member.add_roles(role)


async def handle_reaction_remove(payload: discord.RawReactionActionEvent, bot: discord.Client):
    if payload.guild_id is None:
        return

    data = load_data()
    message_id = str(payload.message_id)

    if message_id not in data:
        return

    config = data[message_id]

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member.bot:
        return

    emoji = str(payload.emoji)

    if emoji not in config["roles"]:
        return

    role_id = config["roles"][emoji]
    role = guild.get_role(role_id)

    if role in member.roles:
        await member.remove_roles(role)
