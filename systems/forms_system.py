import discord
from core.state import State
from utils.emojis import Emojis

# ==========================================
# DATABASE LOGIC (BẢO TỒN 100% DNA CỦA SẾP)
# ==========================================

def _get_forms_col():
    """
    [INDUSTRIAL PRO]
    Truy xuất trực tiếp collection 'forms' từ cỗ máy MongoDB.
    Đã tối ưu để tương thích với Proxy Attribute của hệ thống.
    """
    db = getattr(State.bot, "db", None)
    if not db: return None
    
    # Ưu tiên truy cập trực tiếp qua thuộc tính đã được ánh xạ
    try:
        return db.forms
    except Exception:
        # Kế hoạch dự phòng: Truy cập thẳng vào database thô
        raw_db = getattr(db, "db", None)
        if raw_db is not None:
            return raw_db["forms"]
    return None

async def get_form_config(guild_id: int, embed_name: str):
    """Lấy cấu hình Form cụ thể gắn với định danh Embed."""
    if not embed_name: return None
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        # Truy vấn theo embed_name để hỗ trợ nhiều form khác nhau trong 1 server
        doc = await col.find_one({"guild_id": gid, "embed_name": name})
        return doc if doc else None
    return None

async def get_all_forms(guild_id: int):
    """
    [CẤY MỚI - ATK]
    Bốc toàn bộ danh sách Form của server để hiển thị Dashboard.
    Phục vụ lộ trình theo dõi setup thực tế của sếp.
    """
    gid = str(guild_id)
    col = _get_forms_col()
    if col is not None:
        cursor = col.find({"guild_id": gid})
        return await cursor.to_list(length=100)
    return []

async def update_form_base(guild_id: int, embed_name: str, title: str, log_id: str, thumbnail: bool):
    """Cập nhật thông tin khung (Base) của Form."""
    if not embed_name: return False
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": {
                "form_title": title,
                "log_channel_id": log_id,
                "show_thumbnail": thumbnail
            }},
            upsert=True
        )
        return True
    return False

async def update_form_field(guild_id: int, embed_name: str, slot: int, label: str, placeholder: str, required: bool):
    """Cập nhật dữ liệu chi tiết cho từng ô nhập liệu (Field Slot)."""
    if not embed_name: return False
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        # Cập nhật chính xác vào nested object 'fields' của Form
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": {f"fields.{slot}": {
                "label": label,
                "placeholder": placeholder,
                "required": required
            }}},
            upsert=True
        )
        return True
    return False

# ==========================================
# INTERACTION LOGIC (GIA CỐ KHOẢNG CÁCH)
# ==========================================

class YiyiFormModal(discord.ui.Modal):
    """Lớp giao diện bảng nhập liệu hiện lên khi người dùng bấm nút."""
    def __init__(self, title, fields_data, log_channel_id, show_thumbnail):
        super().__init__(title=title)
        self.log_channel_id = log_channel_id
        self.show_thumbnail = show_thumbnail
        self.inputs = {}

        # Sắp xếp các ô nhập liệu theo đúng thứ tự slot (1 -> 5)
        sorted_slots = sorted(fields_data.keys(), key=lambda x: int(x))

        for slot in sorted_slots:
            data = fields_data[slot]
            text_input = discord.ui.TextInput(
                label=data['label'],
                placeholder=data['placeholder'],
                required=data['required'],
                style=discord.TextStyle.paragraph if len(data['label']) > 15 else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.inputs[slot] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        # Mạch gửi đơn về kênh log khi user nhấn Submit
        channel = interaction.guild.get_channel(int(self.log_channel_id))
        if not channel:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} **yiyi** không tìm thấy kênh gửi log, xin hãy kiểm tra lại cấu hình setup.", ephemeral=True)

        embed_log = discord.Embed(
            title=f"{Emojis.BUOMA} đơn đăng ký mới: {self.title}",
            color=0xe6e2dd,
            timestamp=discord.utils.utcnow()
        )
        
        # [KHOẢNG CÁCH INDUSTRIAL] Ép tạo dòng trống bằng \n\u200b
        # Kỹ thuật này giúp "Người gửi" tách biệt hoàn toàn với các trường bên dưới
        embed_log.add_field(
            name="Người gửi:", 
            value=f"{interaction.user.mention}\n\u200b", 
            inline=False
        )
        
        # Thêm các trường dữ liệu (Gỡ bỏ bullet point để giống ảnh mẫu của sếp)
        for slot in sorted(self.inputs.keys(), key=lambda x: int(x)):
            text_input = self.inputs[slot]
            embed_log.add_field(name=text_input.label, value=text_input.value, inline=False)
        
        # Hiện Avatar nếu sếp bật show_thumbnail
        if self.show_thumbnail:
            embed_log.set_thumbnail(url=interaction.user.display_avatar.url)

        await channel.send(embed=embed_log)
        await interaction.response.send_message(f"{Emojis.BUOMA} đơn đã được gửi đi thành công.", ephemeral=True)

async def handle_forms_interaction(interaction: discord.Interaction):
    """
    [ENTRY POINT] 
    Hàm này điều phối việc hiện Modal khi user bấm nút gắn với Form.
    Nó chính là cái mà button_listener.py đang tìm kiếm.
    """
    custom_id = interaction.data.get("custom_id", "")
    parts = custom_id.split(":")
    if len(parts) < 4: return

    embed_name = parts[3]
    config = await get_form_config(interaction.guild.id, embed_name)

    if not config or not config.get("fields"):
        return await interaction.response.send_message(f"{Emojis.HOICHAM} form này chưa được thiết lập nội dung field.", ephemeral=True)

    # Hiện Modal xịn xò cho user
    modal = YiyiFormModal(
        title=config.get("form_title", "Biểu mẫu Yiyi"),
        fields_data=config.get("fields", {}),
        log_channel_id=config.get("log_channel_id"),
        show_thumbnail=config.get("show_thumbnail", True)
    )
    await interaction.response.send_modal(modal)
