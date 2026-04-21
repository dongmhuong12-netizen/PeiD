import discord
from core.state import State
from core.variable_engine import apply_variables

ACTIVE_EMBED_VIEWS = {}

# =========================
# STATE WRAPPER (FIXED CONSISTENCY)
# =========================

async def load_reaction_data():
    data = await State.get_reaction_data()
    return data or {}

async def save_reaction_data(data):
    await State.set_reaction_data(data)


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
# REACTION ROLE MODAL
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):

    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis = discord.ui.TextInput(
            label="Emojis (cách nhau bằng ,)",
            required=True
        )

        self.roles = discord.ui.TextInput(
            label="Roles (ID hoặc mention, cách nhau bằng ,)",
            required=True
        )

        self.mode = discord.ui.TextInput(
            label="Mode (single/multi)",
            default="single",
            required=True
        )

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

            raw_emojis = [x.strip() for x in self.emojis.value.split(",") if x.strip()]
            raw_roles = [x.strip() for x in self.roles.value.split(",") if x.strip()]
            mode = self.mode.value.lower().strip()

            if len(raw_emojis) != len(raw_roles):
                return await interaction.response.send_message("Emoji và role không khớp.", ephemeral=True)

            if mode not in ["single", "multi"]:
                return await interaction.response.send_message("Mode phải là single hoặc multi.", ephemeral=True)

            parsed_roles = []

            for r in raw_roles:
                role_obj = parse_role(r)
                if not role_obj:
                    return await interaction.response.send_message(f"Role `{r}` không hợp lệ.", ephemeral=True)
                parsed_roles.append([str(role_obj.id)])

            parsed_emojis = raw_emojis

            guild_id = str(guild.id)
            embed_name = self.view.name

            data = await load_reaction_data()
            key = f"{guild_id}:{embed_name}"

            if key not in data:
                data[key] = {
                    "guild_id": guild_id,
                    "embed_name": embed_name,
                    "groups": []
                }

            new_group = {
                "mode": mode,
                "emojis": parsed_emojis,
                "roles": parsed_roles
            }

            if new_group not in data[key]["groups"]:
                data[key]["groups"].append(new_group)

            await save_reaction_data(data)

            await interaction.response.send_message("Reaction role lưu thành công.", ephemeral=True)

        except Exception as e:
            print("ReactionRoleModal ERROR:", e)
            if not interaction.response.is_done():
                await interaction.response.send_message("Có lỗi xảy ra.", ephemeral=True)


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

        if key not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[key] = []

        ACTIVE_EMBED_VIEWS[key].append(self)

        ACTIVE_EMBED_VIEWS[key] = ACTIVE_EMBED_VIEWS[key][-20:]

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
    # BUTTONS (UI ORIGINAL)
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

    # =========================
    # SAVE / DELETE (RESTORED CORE LOGIC)
    # =========================

    @discord.ui.button(label="Save Embed", style=discord.ButtonStyle.success)
    async def save_embed(self, interaction, button):
        from core.embed_storage import save_embed

        save_embed(interaction.guild.id, self.name, self.data)

        await interaction.response.send_message(
            "Embed đã được lưu thành công.",
            ephemeral=True
        )

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_embed(self, interaction, button):
        from core.embed_storage import delete_embed

        delete_embed(interaction.guild.id, self.name)

        key = f"{self.guild_id}:{self.name}"

        if key in ACTIVE_EMBED_VIEWS:
            for v in ACTIVE_EMBED_VIEWS[key]:
                try:
                    if v.message:
                        await v.message.delete()
                except:
                    pass
                v.stop()

            ACTIVE_EMBED_VIEWS[key] = []

        await interaction.response.send_message(
            f"Embed `{self.name}` đã được xoá.",
            ephemeral=True
        )
