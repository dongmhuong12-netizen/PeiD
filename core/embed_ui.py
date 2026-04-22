# core/embed_ui.py
import discord
import asyncio
from core.variable_engine import apply_variables
from core.embed_storage import save_embed, delete_embed
from systems.reaction_role import ReactionRole

ACTIVE_EMBED_VIEWS = {}

# =========================
# STATE WRAPPER (FIXED SOURCE OF TRUTH)
# =========================

async def load_reaction_data():
    from core.cache_manager import load
    return load("reaction_roles") or {}

async def save_reaction_data(data):
    from core.cache_manager import mark_dirty, load

    cache = load("reaction_roles")
    cache.clear()
    cache.update(data)

    mark_dirty("reaction_roles")


# =========================
# MODALS (UNCHANGED LOGIC)
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
            label="Hex Color",
            required=True,
            default=hex(self.view.data.get("color", 0x5865F2)).replace("0x", "").upper()
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.view.data["color"] = int(self.input.value.replace("#", ""), 16)
            await self.view.update_message(interaction)
        except:
            await interaction.response.send_message(
                "❌ Color không hợp lệ",
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
# REACTION ROLE MODAL (FIXED SAFE SAVE)
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis = discord.ui.TextInput(
            label="Emojis (,)",
            required=True
        )

        self.roles = discord.ui.TextInput(
            label="Roles ID/mention (,)",
            required=True
        )

        self.mode = discord.ui.TextInput(
            label="Mode single/multi",
            required=True,
            default="single"
        )

        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        def parse_role(r):
            r = r.strip()
            if r.startswith("<@&") and r.endswith(">"):
                r = r[3:-1]
            if not r.isdigit():
                return None
            return guild.get_role(int(r))

        emojis = [e.strip() for e in self.emojis.value.split(",") if e.strip()]
        roles_raw = [r.strip() for r in self.roles.value.split(",") if r.strip()]
        mode = self.mode.value.lower().strip()

        errors = []

        if len(emojis) != len(roles_raw):
            errors.append("Emoji và role không khớp")

        if mode not in ["single", "multi"]:
            errors.append("Mode sai")

        parsed_roles = []
        for r in roles_raw:
            role = parse_role(r)
            if not role:
                errors.append(f"Role lỗi: {r}")
            else:
                parsed_roles.append([str(role.id)])

        if errors:
            return await interaction.response.send_message(
                "❌ Lỗi:\n- " + "\n- ".join(errors),
                ephemeral=True
            )

        data = await load_reaction_data()

        key = f"{guild.id}:{self.view.name}"

        data.setdefault(key, {
            "guild_id": str(guild.id),
            "embed_name": self.view.name,
            "groups": []
        })

        group = {
            "mode": mode,
            "emojis": emojis,
            "roles": parsed_roles
        }

        data[key]["groups"].append(group)

        await save_reaction_data(data)

        # 🔥 SYNC IMMEDIATE (FIX MẤT PICK EMOJI)
        try:
            msg = self.view.message
            if msg:
                for e in emojis:
                    await msg.add_reaction(e)
        except:
            pass

        await interaction.response.send_message(
            "✅ Reaction role saved",
            ephemeral=True
        )


# =========================
# EMBED VIEW
# =========================

class EmbedUIView(discord.ui.View):

    def __init__(self, guild_id: int, name: str, data: dict):
        super().__init__(timeout=None)

        self.guild_id = str(guild_id)
        self.name = name
        self.data = data
        self.message = None

        key = f"{self.guild_id}:{name}"
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(self)

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

    # =========================
    # BUTTONS
    # =========================

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.secondary)
    async def edit_title(self, interaction, button):
        await interaction.response.send_modal(EditTitleModal(self))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary)
    async def edit_description(self, interaction, button):
        await interaction.response.send_modal(EditDescriptionModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary)
    async def set_image(self, interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction, button):
        await interaction.response.send_modal(EditColorModal(self))

    @discord.ui.button(label="Reaction Roles", style=discord.ButtonStyle.secondary)
    async def reaction_roles(self, interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.success)
    async def save_embed(self, interaction, button):
        save_embed(interaction.guild.id, self.name, self.data)

        await interaction.response.send_message(
            "Saved",
            ephemeral=True
        )

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_embed(self, interaction, button):
        delete_embed(interaction.guild.id, self.name)

        key = f"{self.guild_id}:{self.name}"

        ACTIVE_EMBED_VIEWS.pop(key, None)

        await interaction.response.send_message(
            "Deleted",
            ephemeral=True
        )
