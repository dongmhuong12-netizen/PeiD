# core/embed_ui.py
import discord
import threading

from core.state import State
from core.variable_engine import apply_variables

ACTIVE_EMBED_VIEWS = {}

file_lock = threading.Lock()


# =========================
# EMBED STATE ACCESS (REPLACED STORAGE)
# =========================

def load_reaction_data():
    # fallback sync wrapper for compatibility
    import asyncio
    return asyncio.run(State.get_rt("reaction_roles") or {})


def save_reaction_data(data):
    import asyncio
    asyncio.run(State.set_rt("reaction_roles", data))


# =========================
# EDIT MODALS
# =========================

class EditTitleModal(discord.ui.Modal, title="Edit Title"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.input = discord.ui.TextInput(
            label="New Title",
            required=False,
            default=self.view.data.get("title") or ""
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["title"] = self.input.value
        await self.view.update_message(interaction)


class EditDescriptionModal(discord.ui.Modal, title="Edit Description"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.input = discord.ui.TextInput(
            label="New Description",
            style=discord.TextStyle.paragraph,
            required=False,
            default=self.view.data.get("description") or ""
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["description"] = self.input.value
        await self.view.update_message(interaction)


class EditColorModal(discord.ui.Modal, title="Edit Color (HEX)"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.input = discord.ui.TextInput(
            label="Hex Color (vd: FF0000)",
            required=True,
            default=hex(self.view.data.get("color", 0x5865F2)).replace("0x", "").upper()
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.view.data["color"] = int(self.input.value.replace("#", ""), 16)
            await self.view.update_message(interaction)
        except ValueError:
            await interaction.response.send_message(
                "Mã màu không hợp lệ.",
                ephemeral=True
            )


class EditImageModal(discord.ui.Modal, title="Set Image URL"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.input = discord.ui.TextInput(
            label="Image URL",
            required=False,
            default=self.view.data.get("image") or ""
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["image"] = self.input.value
        await self.view.update_message(interaction)


# =========================
# REACTION ROLE MODAL (UNCHANGED LOGIC, ONLY STORAGE LAYER CHANGED)
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):

    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis = discord.ui.TextInput(label="Emojis (cách nhau bằng ,)", required=True)
        self.roles = discord.ui.TextInput(label="Roles (ID hoặc mention, cách nhau bằng ,)", required=True)
        self.mode = discord.ui.TextInput(label="Mode (single/multi)", default="single", required=True)

        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            if not guild:
                return

            def parse_role(role_input: str):
                role_input = role_input.strip()
                if role_input.startswith("<@&") and role_input.endswith(">"):
                    role_input = role_input[3:-1]
                if not role_input.isdigit():
                    return None
                return guild.get_role(int(role_input))

            def parse_emoji(emoji_input: str):
                emoji_input = emoji_input.strip()

                if emoji_input.startswith("<") and emoji_input.endswith(">"):
                    try:
                        emoji_id = int(emoji_input.split(":")[-1].replace(">", ""))
                        return guild.get_emoji(emoji_id)
                    except:
                        return None

                for e in guild.emojis:
                    if e.name == emoji_input:
                        return e

                return emoji_input

            raw_emojis = [e.strip() for e in self.emojis.value.split(",") if e.strip()]
            raw_roles = [r.strip() for r in self.roles.value.split(",") if r.strip()]
            mode = self.mode.value.lower().strip()

            if len(raw_emojis) != len(raw_roles):
                return await interaction.response.send_message("Emoji và role không khớp.", ephemeral=True)

            if mode not in ["single", "multi"]:
                return await interaction.response.send_message("Mode phải là single hoặc multi.", ephemeral=True)

            parsed_emojis = []
            parsed_roles = []

            for r in raw_roles:
                role_obj = parse_role(r)
                if not role_obj:
                    return await interaction.response.send_message(f"Role `{r}` không hợp lệ.", ephemeral=True)
                parsed_roles.append([str(role_obj.id)])

            for e in raw_emojis:
                emoji_obj = parse_emoji(e)
                parsed_emojis.append(str(emoji_obj))

            guild_id = guild.id
            embed_name = self.view.name

            data = load_reaction_data()
            key = f"{guild_id}::embed::{embed_name}"

            new_group = {
                "mode": mode,
                "emojis": parsed_emojis,
                "roles": parsed_roles
            }

            if key not in data:
                data[key] = {
                    "guild_id": guild_id,
                    "embed_name": embed_name,
                    "groups": []
                }

            if new_group not in data[key]["groups"]:
                data[key]["groups"].append(new_group)

            save_reaction_data(data)

            await interaction.response.send_message(
                "Reaction role lưu thành công.",
                ephemeral=True
            )

        except Exception as e:
            print("ReactionRoleModal ERROR:", e)


# =========================
# EMBED VIEW (UNCHANGED LOGIC)
# =========================

class EmbedUIView(discord.ui.View):

    def __init__(self, guild_id: int, name: str, data: dict):
        super().__init__(timeout=None)

        self.name = name
        self.data = data
        self.message = None

        key = f"{guild_id}::{name}"

        if key not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[key] = []

        ACTIVE_EMBED_VIEWS[key].append(self)

        if len(ACTIVE_EMBED_VIEWS[key]) > 25:
            ACTIVE_EMBED_VIEWS[key] = ACTIVE_EMBED_VIEWS[key][-25:]

    def build_embed(self):
        data = self.data.copy()

        if hasattr(self, "guild") and hasattr(self, "member"):
            data = apply_variables(data, self.guild, self.member)

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color", 0x5865F2)
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        return embed

    async def update_message(self, interaction: discord.Interaction):
        self.guild = interaction.guild
        self.member = interaction.user

        embed = self.build_embed()

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.secondary)
    async def edit_title(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary)
    async def set_image(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(EditColorModal(self))

    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.secondary)
    async def reaction_roles(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))
