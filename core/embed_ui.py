import discord
import asyncio
import copy
import re
from core.variable_engine import apply_variables
from core.embed_storage import save_embed, delete_embed
# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
from core.state import State
from utils.emojis import Emojis

ACTIVE_EMBED_VIEWS = {}
REACTION_FILE_KEY = "reaction_roles"

# [VÁ LỖI] Lock để bảo vệ dữ liệu reaction role
_reaction_lock = asyncio.Lock()

# =========================
# STATE WRAPPER (ATOMIC)
# =========================

async def load_reaction_data():
    """
    [TRÍ NHỚ ĐÃ BÓC TÁCH]
    Logic nạp dữ liệu từ tệp cục bộ đã bị gỡ bỏ.
    Dữ liệu sẽ được nạp thông qua lớp Storage mới của cậu.
    """
    return {}

async def save_reaction_data(data):
    """
    [TRÍ NHỚ ĐÃ BÓC TÁCH]
    Vô hiệu hóa việc đánh dấu dirty để ghi file.
    """
    pass

# =========================
# MODALS
# =========================

class EditInformationModal(discord.ui.Modal, title="edit information"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        
        curr_title = self.view.data.get("title")
        is_default_title = curr_title in ["Tiêu đề Embed mới", "tiêu đề embed mới", "embed mới", None]
        
        self.etitle = discord.ui.TextInput(
            label="tiêu đề mới",
            placeholder="tiêu đề embed mới",
            required=False,
            default=None if is_default_title else curr_title
        )
        
        curr_desc = self.view.data.get("description")
        is_default_desc = curr_desc in ["Nội dung mô tả mặc định", "Nội dung mô tả mặc định.", "nội dung mô tả mặc định", "nội dung mô tả", None]
        
        self.description = discord.ui.TextInput(
            label="mô tả mới",
            style=discord.TextStyle.paragraph,
            placeholder="nội dung mô tả mặc định",
            required=False,
            default=None if is_default_desc else curr_desc
        )
        
        curr_color_hex = hex(self.view.data.get("color", 0xe6e2dd)).replace("0x", "").lower()
        
        self.color = discord.ui.TextInput(
            label="mã màu hex",
            placeholder="e6e2dd",
            required=True,
            default=curr_color_hex 
        )
        
        self.add_item(self.etitle)
        self.add_item(self.description)
        self.add_item(self.color)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # [CẤY GHÉP INDUSTRIAL] Logic xóa trắng dữ liệu an toàn
        title_val = self.etitle.value.strip().lower()
        if not title_val or title_val == "none":
            self.view.data.pop("title", None)
        else:
            self.view.data["title"] = self.etitle.value

        desc_val = self.description.value.strip().lower()
        if not desc_val or desc_val == "none":
            self.view.data.pop("description", None)
        else:
            self.view.data["description"] = self.description.value
            
        # [PHAO CỨU SINH 400 BAD REQUEST] Nếu cả title và desc đều bị pop mất, cấy khoảng trắng tàng hình
        if "title" not in self.view.data and "description" not in self.view.data:
            self.view.data["description"] = "\u200b"
        
        try:
            val = self.color.value.replace("#", "").lower() or "e6e2dd"
            self.view.data["color"] = int(val, 16)
            
            await save_embed(self.view.guild_id, self.view.name, self.view.data)
            # [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ ép ghi đĩa cục bộ
            
            await self.view.update_message(interaction)
        except:
            await interaction.followup.send("sai mã màu, xin hãy nhập lại", ephemeral=True)

class EditAuthorModal(discord.ui.Modal, title="edit author details"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        auth = self.view.data.get("author", {})
        
        self.name = discord.ui.TextInput(
            label="tên tác giả", 
            placeholder="nhập tên...", 
            default=auth.get("name") or "", 
            required=False
        )
        self.icon = discord.ui.TextInput(
            label="url ảnh tác giả", 
            placeholder="https://...", 
            default=auth.get("icon_url") or "", 
            required=False
        )
        self.url = discord.ui.TextInput(
            label="url liên kết tác giả", 
            placeholder="https://...", 
            default=auth.get("url") or "", 
            required=False
        )
        
        self.add_item(self.name)
        self.add_item(self.icon)
        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.view.data["author"] = {
            "name": self.name.value,
            "icon_url": self.icon.value,
            "url": self.url.value
        }
        
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await self.view.update_message(interaction)

class EditFooterModal(discord.ui.Modal, title="edit footer details"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        foot = self.view.data.get("footer", {})
        
        self.text = discord.ui.TextInput(
            label="nội dung chân trang", 
            placeholder="nhập nội dung...", 
            default=foot.get("text") or "", 
            required=False
        )
        self.icon = discord.ui.TextInput(
            label="url ảnh chân trang", 
            placeholder="https://...", 
            default=foot.get("icon_url") or "", 
            required=False
        )
        self.timestamp = discord.ui.TextInput(
            label="hiển thị thời gian? (yes/no)", 
            placeholder="yes hoặc no",
            default=self.view.data.get("timestamp") or "no",
            required=False
        )
        
        self.add_item(self.text)
        self.add_item(self.icon)
        self.add_item(self.timestamp)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.view.data["footer"] = {
            "text": self.text.value,
            "icon_url": self.icon.value
        }
        self.view.data["timestamp"] = self.timestamp.value.lower().strip()
        
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await self.view.update_message(interaction)

class EditImageModal(discord.ui.Modal, title="set image & thumbnail url"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        
        self.image_input = discord.ui.TextInput(
            label="url hình ảnh chính",
            placeholder="https://... hoặc dùng {user_avatar}",
            required=False,
            default=self.view.data.get("image") or ""
        )
        
        self.thumbnail = discord.ui.TextInput(
            label="thumbnail (avt góc phải)",
            placeholder="https://... hoặc dùng {user_avatar}",
            required=False,
            default=self.view.data.get("thumbnail") or ""
        )
        
        self.add_item(self.image_input)
        self.add_item(self.thumbnail)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.view.data["image"] = self.image_input.value
        self.view.data["thumbnail"] = self.thumbnail.value
        
        await save_embed(self.view.guild_id, self.view.name, self.view.data)
        await self.view.update_message(interaction)

class ReactionRoleModal(discord.ui.Modal, title="reaction role setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        current = self.view.temp_reaction_data or {}
        
        self.emojis = discord.ui.TextInput(
            label="emojis (ngăn cách bằng dấu phẩy)", 
            placeholder="emoji1, emoji2, emoji3",
            default=", ".join(current.get("emojis", [])),
            required=True
        )
        self.roles = discord.ui.TextInput(
            label="roles (id hoặc mention)", 
            placeholder="id1, id2, id3",
            default=", ".join(current.get("roles_raw", [])),
            required=True
        )
        
        curr_mode = current.get("mode")
        self.mode = discord.ui.TextInput(
            label="chế độ (single/multi)", 
            placeholder="single hoặc multi",
            required=True, 
            default="" if curr_mode in ["single", None] else curr_mode
        )
        
        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        emojis = [e.strip() for e in self.emojis.value.split(",") if e.strip()]
        roles_raw = [r.strip() for r in self.roles.value.split(",") if r.strip()]
        mode = self.mode.value.lower().strip() or "single"

        errors = []
        if len(emojis) != len(roles_raw):
            errors.append(f"số lượng emoji (`{len(emojis)}`) và role (`{len(roles_raw)}`) không khớp.")

        parsed_role_ids = []
        for r_raw in roles_raw:
            rid = self.view._parse_role_id(r_raw)
            role = guild.get_role(int(rid)) if rid and rid.isdigit() else None
            if not role:
                errors.append(f"không tìm thấy role: `{r_raw}`")
            else:
                parsed_role_ids.append(str(role.id))

        if errors:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi cấu hình reaction role",
                description="xin hãy nhập lại\n- " + "\n- ".join(errors),
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err, ephemeral=True)

        # [VÁ LỖI] Sử dụng Lock để tránh tranh chấp
        async with _reaction_lock:
            # Logic lưu dữ liệu reaction role tại đây sẽ được cậu cấy MongoDB vào
            pass
        
        self.view.temp_reaction_data = {"emojis": emojis, "roles_raw": roles_raw, "mode": mode}
        await save_embed(self.view.guild_id, self.view.name, self.view.data)

        from core.embed_sender import _enqueue_reaction
        if self.view.message:
            for e in emojis:
                await _enqueue_reaction(self.view.message, e)
            await State.atomic_embed_register(guild.id, self.view.name, self.view.message.id)

        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật reaction role cho `{self.view.name}` thành công",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success, ephemeral=False)

# =========================
# MAIN VIEW
# =========================

class EmbedUIView(discord.ui.View):
    def __init__(self, guild_id: int, name: str, data: dict, timeout: float = 600.0):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)
        self.name = name
        self.data = data
        self.message = None
        self.temp_reaction_data = None
        
        # [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ nạp reaction role từ cache cục bộ
        
        key = f"{self.guild_id}:{name}"
        if key in ACTIVE_EMBED_VIEWS:
            for old_view in ACTIVE_EMBED_VIEWS[key]:
                try: old_view.stop()
                except: pass
        ACTIVE_EMBED_VIEWS[key] = [self]

        self.add_item(discord.ui.Button(
            label="need help? join support server", 
            url="https://discord.gg/EK6pf8nCM3", 
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
        
        if data_copy.get("title") in ["Tiêu đề Embed mới", "tiêu đề embed mới", "embed mới"]:
            data_copy["title"] = "tiêu đề embed mới"
        if data_copy.get("description") in ["Nội dung mô tả mặc định", "Nội dung mô tả mặc định.", "nội dung mô tả mặc định", "nội dung mô tả"]:
            data_copy["description"] = "nội dung mô tả mặc định"
        
        if data_copy.get("color") in [0x5865f2, 0x5865F2, None]:
            data_copy["color"] = 0xe6e2dd
            
        if guild:
            data_copy = apply_variables(data_copy, guild, member)

        # =========================================================================
        # [MẠCH VÁ LỖI NỘI SUY EMOJI]
        # Tự động quét chuỗi {Emojis.TÊN_BIẾN} và dịch sang mã Graphic thời gian thực
        # =========================================================================
        def translate_emoji_tags(text):
            if not isinstance(text, str): return text
            return re.sub(r'\{Emojis\.([A-Za-z0-9_]+)\}', lambda m: str(getattr(Emojis, m.group(1).upper(), m.group(0))), text)

        if "title" in data_copy:
            data_copy["title"] = translate_emoji_tags(data_copy["title"])
        if "description" in data_copy:
            data_copy["description"] = translate_emoji_tags(data_copy["description"])
        if "footer" in data_copy and isinstance(data_copy["footer"], dict) and "text" in data_copy["footer"]:
            data_copy["footer"]["text"] = translate_emoji_tags(data_copy["footer"]["text"])
        if "author" in data_copy and isinstance(data_copy["author"], dict) and "name" in data_copy["author"]:
            data_copy["author"]["name"] = translate_emoji_tags(data_copy["author"]["name"])
        if "fields" in data_copy and isinstance(data_copy["fields"], list):
            for field in data_copy["fields"]:
                if "name" in field: field["name"] = translate_emoji_tags(field["name"])
                if "value" in field: field["value"] = translate_emoji_tags(field["value"])
        # =========================================================================

        return _build_embed(data_copy)

    async def update_message(self, interaction: discord.Interaction):
        embed = self.build_embed(interaction.guild, interaction.user)
        self.message = interaction.message or self.message
        
        if interaction.response.is_done():
            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except:
                if self.message:
                    await self.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    def _parse_role_id(self, raw_str: str):
        match = re.search(r'\d+', raw_str)
        return match.group() if match else None

    @discord.ui.button(label="edit information (tiêu đề / mô tả / màu sắc)", style=discord.ButtonStyle.secondary, row=0, custom_id="yiyi:embed:edit_info")
    async def edit_info(self, interaction, button):
        await interaction.response.send_modal(EditInformationModal(self))

    @discord.ui.button(label="edit author", style=discord.ButtonStyle.secondary, row=1, custom_id="yiyi:embed:edit_author")
    async def edit_author(self, interaction, button):
        await interaction.response.send_modal(EditAuthorModal(self))

    @discord.ui.button(label="edit footer", style=discord.ButtonStyle.secondary, row=1, custom_id="yiyi:embed:edit_footer")
    async def edit_footer(self, interaction, button):
        await interaction.response.send_modal(EditFooterModal(self))

    @discord.ui.button(label="set image", style=discord.ButtonStyle.secondary, row=1, custom_id="yiyi:embed:set_image")
    async def set_image(self, interaction, button):
        await interaction.response.send_modal(EditImageModal(self))

    @discord.ui.button(label="reaction roles (cài đặt emoji và role)", style=discord.ButtonStyle.secondary, row=2, custom_id="yiyi:embed:reaction_roles")
    async def reaction_roles(self, interaction, button):
        await interaction.response.send_modal(ReactionRoleModal(self))
