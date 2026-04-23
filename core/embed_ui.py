import discord
import asyncio
import copy
import re
from core.variable_engine import apply_variables
from core.embed_storage import save_embed, delete_embed
from systems.reaction_role import ReactionRole
from core.cache_manager import load, mark_dirty, get_raw
from core.state import State

ACTIVE_EMBED_VIEWS = {}

# =========================
# STATE WRAPPER (Quy tắc 2: Tối ưu Storage)
# =========================

async def load_reaction_data():
    # Sử dụng get_raw để đảm bảo tính thời gian thực cho 100k servers
    return get_raw("reaction_roles")

async def save_reaction_data(data):
    # Dữ liệu đã được sửa trực tiếp qua get_raw, chỉ cần mark_dirty
    mark_dirty("reaction_roles")


# =========================
# MODALS
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


# =========================
# REACTION ROLE MODAL (FIXED)
# =========================

class ReactionRoleModal(discord.ui.Modal, title="Reaction Role Setup"):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self.emojis = discord.ui.TextInput(
            label="Emojis (Cách nhau bằng dấu phẩy)", 
            placeholder="😀, 😎, ❤️",
            required=True
        )
        self.roles = discord.ui.TextInput(
            label="Roles (ID hoặc Mention)", 
            placeholder="ID1, ID2 hoặc @role1, @role2",
            required=True
        )
        self.mode = discord.ui.TextInput(
            label="Mode (single/multi)", 
            required=True, 
            default="single"
        )

        self.add_item(self.emojis)
        self.add_item(self.roles)
        self.add_item(self.mode)

    async def on_submit(self, interaction: discord.Interaction):
        # Chấp nhận dữ liệu thô để xử lý sau (Quy tắc: Linh hoạt đầu vào)
        self.view.temp_reaction_data = {
            "emojis": [e.strip() for e in self.emojis.value.split(",") if e.strip()],
            "roles_raw": [r.strip() for r in self.roles.value.split(",") if r.strip()],
            "mode": self.mode.value.lower().strip()
        }
        
        await interaction.response.send_message(
            "✅ Đã ghi nhận Reaction Roles. Vui lòng nhấn **Save Embed** để hoàn tất kiểm tra và áp dụng.", 
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
        # Biến tạm lưu reaction roles trước khi save
        self.temp_reaction_data = None

        key = f"{self.guild_id}:{name}"
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(self)

    def build_embed(self):
        data = copy.deepcopy(self.data)

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
        self.message = interaction.message

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    # =========================
    # INTERNAL HELPERS (Quy tắc 10/10: Smart Parser)
    # =========================

    def _parse_role_id(self, raw_str: str):
        """Lọc sạch mọi ký tự lạ để lấy đúng ID Role"""
        # Regex lấy toàn bộ dãy số trong chuỗi (xử lý cả <@&ID>, ID, hoặc văn bản lạ)
        match = re.search(r'\d+', raw_str)
        return match.group() if match else None

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
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        errors = []
        
        # 1. Xử lý Reaction Roles nếu có thay đổi
        if self.temp_reaction_data:
            emojis = self.temp_reaction_data["emojis"]
            roles_raw = self.temp_reaction_data["roles_raw"]
            mode = self.temp_reaction_data["mode"]

            if len(emojis) != len(roles_raw):
                errors.append(f"Số lượng Emoji ({len(emojis)}) và Role ({len(roles_raw)}) không khớp.")

            if mode not in ["single", "multi"]:
                errors.append("Chế độ (Mode) chỉ có thể là 'single' hoặc 'multi'.")

            parsed_role_ids = []
            for r_raw in roles_raw:
                rid = self._parse_role_id(r_raw)
                role = guild.get_role(int(rid)) if rid and rid.isdigit() else None
                
                if not role:
                    errors.append(f"Không tìm thấy Role: `{r_raw}`")
                else:
                    parsed_role_ids.append(str(role.id))

            if not errors:
                # Lưu vào storage nếu không có lỗi
                data = await load_reaction_data()
                key = f"{guild.id}:{self.name}"
                
                data[key] = {
                    "guild_id": str(guild.id),
                    "embed_name": self.name,
                    "groups": [{
                        "mode": mode,
                        "emojis": emojis,
                        "roles": parsed_role_ids
                    }]
                }
                await save_reaction_data(data)
                
                # Thêm reaction vào tin nhắn (Back-end xử lý, không làm kẹt UI)
                if self.message:
                    for e in emojis:
                        try:
                            await self.message.add_reaction(e)
                            await asyncio.sleep(0.1) # Tránh Rate Limit
                        except: pass

        if errors:
            return await interaction.followup.send(
                "❌ **Lưu thất bại! Phát hiện lỗi cấu hình:**\n- " + "\n- ".join(errors), 
                ephemeral=True
            )

        # 2. Lưu Embed Data chính
        save_embed(interaction.guild.id, self.name, self.data)

        if self.message:
            await State.atomic_embed_register(
                interaction.guild.id,
                self.name,
                self.message.id,
                None
            )

        await interaction.followup.send(f"✅ Đã lưu thành công Embed: **{self.name}**", ephemeral=True)

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.danger)
    async def delete_embed(self, interaction, button):
        delete_embed(interaction.guild.id, self.name)
        key = f"{self.guild_id}:{self.name}"
        ACTIVE_EMBED_VIEWS.pop(key, None)
        await interaction.response.send_message("Deleted", ephemeral=True)
