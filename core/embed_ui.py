import discord
import asyncio
import copy
import re
from core.variable_engine import apply_variables
from core.embed_storage import save_embed, delete_embed
from core.cache_manager import load, mark_dirty, get_raw, save as force_save
from core.state import State

# Quản lý View thông minh (BẢO TỒN NGUYÊN VẸN 100%)
ACTIVE_EMBED_VIEWS = {}
REACTION_FILE_KEY = "reaction_roles"

# =========================
# STATE WRAPPER (ATOMIC) - GIỮ NGUYÊN TỪNG CHỮ
# =========================

async def load_reaction_data():
    return get_raw(REACTION_FILE_KEY)

async def save_reaction_data(data):
    mark_dirty(REACTION_FILE_KEY)

# =========================
# MODALS (AUTO-SAVE MODE: LƯU TỨC THÌ KHI SUBMIT)
# =========================

class EditInformationModal(discord.ui.Modal, title="Edit Information"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.etitle = discord.ui.TextInput(
            label="New Title",
            required=False,
            default=self.view.data.get("title") or ""
        )
        self.description = discord.ui.TextInput(
            label="New Description",
            style=discord.TextStyle.paragraph,
            required=False,
            default=self.view.data.get("description") or ""
        )
        self.color = discord.ui.TextInput(
            label="Hex Color",
            required=True,
            default=hex(self.view.data.get("color", 0x5865F2)).replace("0x", "").upper()
        )
        self.add_item(self.etitle)
        self.add_item(self.description)
        self.add_item(self.color)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["title"] = self.etitle.value
        self.view.data["description"] = self.description.value
        try:
            val = self.color.value.replace("#", "")
            self.view.data["color"] = int(val, 16)
            
            # --- MẠCH AUTO SAVE ---
            await save_embed(self.view.guild_id, self.view.name, self.view.data)
            await force_save("embeds")
            
            await self.view.update_message(interaction)
        except:
            # GIỮ NGUYÊN BẮT LỖI CỦA CẬU
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Color không hợp lệ", ephemeral=True)

class EditAuthorModal(discord.ui.Modal, title="Edit Author Details"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        auth = self.view.data.get("author", {})
        self.name = discord.ui.TextInput(label="Author Name", default=auth.get("name") or "", required=False)
        self.icon = discord.ui.TextInput(label="Author Icon URL", default=auth.get("icon_url") or "", required=False)
        self.url = discord.ui.TextInput(label="Author Link URL", default=auth.get("url") or "", required=False)
        self.add_item(self.name)
        self.add_item(self.icon)
        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["author"] = {
            "name": self.name.value,
            "icon_url": self.icon.value,
            "url": self.url.value
        }
        
        # --- MẠCH AUTO SAVE ---
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await force_save("embeds")
        
        await self.view.update_message(interaction)

class EditFooterModal(discord.ui.Modal, title="Edit Footer Details"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        foot = self.view.data.get("footer", {})
        self.text = discord.ui.TextInput(label="Footer Text", default=foot.get("text") or "", required=False)
        self.icon = discord.ui.TextInput(label="Footer Icon URL", default=foot.get("icon_url") or "", required=False)
        # MẠCH TIMESTAMP
        self.timestamp = discord.ui.TextInput(
            label="Show Timestamp? (yes/no)", 
            default=self.view.data.get("timestamp") or "no",
            required=False
        )
        self.add_item(self.text)
        self.add_item(self.icon)
        self.add_item(self.timestamp)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.data["footer"] = {
            "text": self.text.value,
            "icon_url": self.icon.value
        }
        self.view.data["timestamp"] = self.timestamp.value.lower().strip()
        
        # --- MẠCH AUTO SAVE ---
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await force_save("embeds")
        
        await self.view.update_message(interaction)

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
        
        # --- MẠCH AUTO SAVE ---
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await force_save("embeds")
        
        await self.view.update_message(interaction)

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        current = self.view.temp_reaction_data or {}
        
        # KHÔI PHỤC PLACEHOLDER CỦA CẬU
        self.emojis = discord.ui.TextInput(
            label="Emojis (comma separated)", 
            placeholder="😀, 😎, ❤️",
            default=", ".join(current.get("emojis", [])),
            required=True
        )
        self.roles = discord.ui.TextInput(
            label="Roles (ID or Mention)", 
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
        guild = interaction.guild
        emojis = [e.strip() for e in self.emojis.value.split(",") if e.strip()]
        roles_raw = [r.strip() for r in self.roles.value.split(",") if r.strip()]
        mode = self.mode.value.lower().strip()

        # BẢO TỒN 100% LOGIC CHECK LỖI TỪ NÚT SAVE CŨ CỦA CẬU
        errors = []
        if len(emojis) != len(roles_raw):
            errors.append(f"Số lượng Emoji ({len(emojis)}) và Role ({len(roles_raw)}) không khớp.")

        parsed_role_ids = []
        for r_raw in roles_raw:
            rid = self.view._parse_role_id(r_raw)
            role = guild.get_role(int(rid)) if rid and rid.isdigit() else None
            if not role:
                errors.append(f"Không tìm thấy Role: `{r_raw}`")
            else:
                parsed_role_ids.append(str(role.id))

        if errors:
            return await interaction.response.send_message("❌ **Configuration Error:**\n- " + "\n- ".join(errors), ephemeral=True)

        # --- TIẾN HÀNH AUTO SAVE (Chuyển từ nút Save cũ vào đây) ---
        db = await load_reaction_data()
        key = f"{guild.id}:{self.view.name}"
        db[key] = {
            "guild_id": str(guild.id),
            "embed_name": self.view.name,
            "groups": [{"mode": mode, "emojis": emojis, "roles": parsed_role_ids}]
        }
        await save_reaction_data(db)
        await force_save(REACTION_FILE_KEY) # ÉP LƯU
        
        # Cập nhật RAM State
        self.view.temp_reaction_data = {
            "emojis": emojis,
            "roles_raw": roles_raw,
            "mode": mode
        }
        
        # Đảm bảo Embed Data chính cũng được lưu
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await force_save("embeds")

        from core.embed_sender import _enqueue_reaction
        if self.view.message:
            # KHÔI PHỤC LOG DNA
            print(f"[UI] Đang đẩy reaction cho {self.view.name} vào hàng đợi...", flush=True)
            for e in emojis:
                await _enqueue_reaction(self.view.message, e)
            
            # Khôi phục Atomic Register DNA
            await State.atomic_embed_register(guild.id, self.view.name, self.view.message.id)

        # KHÔI PHỤC LOG THÀNH CÔNG DNA
        print(f"[UI] Đã lưu thành công Embed: {self.view.name} cho Guild: {guild.id}", flush=True)

        if not interaction.response.is_done():
            await interaction.response.send_message(f"✅ Auto-saved Reaction Roles for `{self.view.name}`", ephemeral=True)

# =========================
# MAIN VIEW (CÂN BẰNG MOBILE & GIỮ NGUYÊN LOGIC)
# =========================

class EmbedUIView(discord.ui.View):
    def __init__(self, guild_id: int, name: str, data: dict, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.guild_id = str(guild_id)
        self.name = name
        self.data = data
        self.message = None
        self.temp_reaction_data = None
        
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
        if key not in ACTIVE_EMBED_VIEWS:
            ACTIVE_EMBED_VIEWS[key] = []
        if self not in ACTIVE_EMBED_VIEWS[key]:
            ACTIVE_EMBED_VIEWS[key].append(self)

        # HÀNG 3: JOIN SERVER (TEXT DÀI CÂN ĐỐI)
        self.add_item(discord.ui.Button(
            label="need help? join support server", 
            url="https://discord.gg/wqfYZVEjgg", 
            row=3
        ))

    async def on_timeout(self):
        key = f"{self.guild_id}:{self.name}"
        if key in ACTIVE_EMBED_VIEWS:
            if self in ACTIVE_EMBED_VIEWS[key]:
                ACTIVE_EMBED_VIEWS[key].remove(self)
        self.stop()

    def build_embed(self, guild=None, member=None):
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

    # --- BUTTONS (BẢO TỒN DNA - XÓA NÚT SAVE/DELETE) ---
    
    @discord.ui.button(label="Edit Information (Title / Description / Color)", style=discord.ButtonStyle.secondary, row=0)
    async def edit_info(self, interaction, button):
        await interaction.response.send_modal(EditInformationModal(self))

    @discord.ui.button(label="Edit Author", style=discord.ButtonStyle.secondary, row=1)
    async def edit_author(self, interaction, button):
        await interaction.response.send_modal(EditAuthorModal(self))

    @discord.ui.button(label="Edit Footer", style=discord.ButtonStyle.secondary, row=1)
    async def edit_footer(self, interaction, button):
        await interaction.response.send_modal(EditFooterModal(self))

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary, row=1)
    async def set_image(self, interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="Reaction Roles (Setup emojis and roles)", style=discord.ButtonStyle.secondary, row=2)
    async def reaction_roles(self, interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))

