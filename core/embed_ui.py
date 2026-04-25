import discord
import asyncio
import copy
import re
from core.variable_engine import apply_variables
from core.embed_storage import save_embed, delete_embed
from core.cache_manager import load, mark_dirty, get_raw
from core.state import State

# Quản lý View thông minh (Sẽ tự dọn dẹp theo timeout)
ACTIVE_EMBED_VIEWS = {}
REACTION_FILE_KEY = "reaction_roles"

# =========================
# STATE WRAPPER (ATOMIC)
# =========================

async def load_reaction_data():
    return get_raw(REACTION_FILE_KEY)

async def save_reaction_data(data):
    mark_dirty(REACTION_FILE_KEY)

# =========================
# MODALS (ANT-TIMEOUT LAYER)
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
            val = self.input.value.replace("#", "")
            self.view.data["color"] = int(val, 16)
            await self.view.update_message(interaction)
        except:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Color không hợp lệ", ephemeral=True)

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

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        current = self.view.temp_reaction_data or {}
        
        self.emojis = discord.ui.TextInput(
            label="Emojis (Cách nhau bằng dấu phẩy)", 
            placeholder="😀, 😎, ❤️",
            default=", ".join(current.get("emojis", [])),
            required=True
        )
        self.roles = discord.ui.TextInput(
            label="Roles (ID hoặc Mention)", 
            placeholder="ID1, ID2...",
            default=", ".join(current.get("roles_raw", [])),
            required=True
        )
        self.mode = discord.ui.TextInput(
            label="Mode (single/multi)", 
            required=True, 
            default=current.get("mode", "single")
        )

        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.temp_reaction_data = {
            "emojis": [e.strip() for e in self.emojis.value.split(",") if e.strip()],
            "roles_raw": [r.strip() for r in self.roles.value.split(",") if r.strip()],
            "mode": self.mode.value.lower().strip()
        }
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "✅ Đã ghi nhận Reaction Roles. Vui lòng nhấn **Save Embed** để áp dụng.", 
                ephemeral=True
            )

# =========================
# MAIN VIEW (MEMORY SAFE)
# =========================

class EmbedUIView(discord.ui.View):
    def __init__(self, guild_id: int, name: str, data: dict):
        # TIÊU CHUẨN 100K+: Giải phóng RAM sau 10 phút không tương tác
        super().__init__(timeout=600)

        self.guild_id = str(guild_id)
        self.name = name
        self.data = data
        self.message = None
        self.temp_reaction_data = None
        
        # Nạp dữ liệu cũ (Trí nhớ tuyệt đối)
        db = get_raw(REACTION_FILE_KEY)
        storage_key = f"{self.guild_id}:{self.name}"
        if storage_key in db:
            config = db[storage_key]
            if config.get("groups"):
                group = config["groups"][0]
                self.temp_reaction_data = {
                    "emojis": group.get("emojis", []),
                    "roles_raw": group.get("roles", []),
                    "mode": group.get("mode", "single")
                }

        key = f"{self.guild_id}:{name}"
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(self)

    async def on_timeout(self):
        """Cleanup logic khi View hết hạn"""
        key = f"{self.guild_id}:{self.name}"
        if key in ACTIVE_EMBED_VIEWS:
            if self in ACTIVE_EMBED_VIEWS[key]:
                ACTIVE_EMBED_VIEWS[key].remove(self)
        self.stop()

    def build_embed(self, guild=None, member=None):
        # Tránh Circular Import bằng Local Import
        from core.embed_sender import _build_embed
        
        data_copy = copy.deepcopy(self.data)
        if guild:
            data_copy = apply_variables(data_copy, guild, member)

        return _build_embed(data_copy)

    async def update_message(self, interaction: discord.Interaction):
        embed = self.build_embed(interaction.guild, interaction.user)
        self.message = interaction.message
        
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    def _parse_role_id(self, raw_str: str):
        match = re.search(r'\d+', raw_str)
        return match.group() if match else None

    # --- BUTTONS ---
    
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
    async def save_embed_btn(self, interaction, button):
        # DEFER NGAY LẬP TỨC: Chống lỗi 3s
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        errors = []
        
        if self.temp_reaction_data:
            emojis = self.temp_reaction_data["emojis"]
            roles_raw = self.temp_reaction_data["roles_raw"]
            mode = self.temp_reaction_data["mode"]

            if len(emojis) != len(roles_raw):
                errors.append(f"Số lượng Emoji ({len(emojis)}) và Role ({len(roles_raw)}) không khớp.")

            parsed_role_ids = []
            for r_raw in roles_raw:
                rid = self._parse_role_id(r_raw)
                role = guild.get_role(int(rid)) if rid and rid.isdigit() else None
                if not role:
                    errors.append(f"Không tìm thấy Role: `{r_raw}`")
                else:
                    parsed_role_ids.append(str(role.id))

            if not errors:
                db = await load_reaction_data()
                key = f"{guild.id}:{self.name}"
                db[key] = {
                    "guild_id": str(guild.id),
                    "embed_name": self.name,
                    "groups": [{"mode": mode, "emojis": emojis, "roles": parsed_role_ids}]
                }
                await save_reaction_data(db)
                
                # Local Import để tránh Circular Import
                from core.embed_sender import _enqueue_reaction
                if self.message:
                    print(f"[UI] Đang đẩy reaction cho {self.name} vào hàng đợi...", flush=True)
                    for e in emojis:
                        await _enqueue_reaction(self.message, e)

        if errors:
            return await interaction.followup.send("❌ **Lỗi cấu hình:**\n- " + "\n- ".join(errors), ephemeral=True)

        save_embed(interaction.guild.id, self.name, self.data)
        
        if self.message:
            await State.atomic_embed_register(interaction.guild.id, self.name, self.message.id)

        print(f"[UI] Đã lưu thành công Embed: {self.name} cho Guild: {guild.id}", flush=True)
        await interaction.followup.send(f"✅ Đã lưu Embed: **{self.name}**", ephemeral=True)

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_embed_btn(self, interaction, button):
        delete_embed(interaction.guild.id, self.name)
        key = f"{self.guild_id}:{self.name}"
        ACTIVE_EMBED_VIEWS.pop(key, None)
        
        if not interaction.response.is_done():
            await interaction.response.send_message(f"🗑️ Đã xóa Embed: **{self.name}**", ephemeral=True)
        
        self.stop()
