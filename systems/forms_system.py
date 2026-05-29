import discord
from core.state import State
from utils.emojis import Emojis

# ==========================================
# LÕI BỘ NHỚ ĐỆM RAM CACHE (ANTI-TIMEOUT O(1))
# ==========================================
# Cấu trúc lưu trữ siêu tốc: { "guild_id": { "embed_name": doc_config_dict } }
FORMS_CACHE = {}

async def init_forms_cache():
    """
    [DEF - NEW INJECTION] 
    Tải toàn bộ cấu trúc cấu hình Form từ MongoDB lên RAM khi khởi động bot.
    """
    global FORMS_CACHE
    col = _get_forms_col()
    if col is not None:
        try:
            FORMS_CACHE.clear()
            cursor = col.find({})
            async for doc in cursor:
                gid = str(doc.get("guild_id"))
                name = str(doc.get("embed_name", "")).lower().strip()
                if gid and name:
                    if gid not in FORMS_CACHE:
                        FORMS_CACHE[gid] = {}
                    FORMS_CACHE[gid][name] = doc
            print("[FORMS-SYSTEM] Bộ nhớ đệm RAM Cache đã nạp vèo vèo thành công!", flush=True)
        except Exception as e:
            print(f"[FORMS-SYSTEM ERROR] Thất bại khi nạp đạn lên bộ nhớ RAM: {e}", flush=True)

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
    """Lấy cấu hình Form (Ưu tiên RAM siêu tốc, có bảo hiểm DB)"""
    if not embed_name: return None
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    
    # 1. LỚP BẢO VỆ CHÍNH: Quét RAM Cache (O(1)) - Tránh Timeout
    if gid in FORMS_CACHE and name in FORMS_CACHE[gid]:
        return FORMS_CACHE[gid][name]
        
    # 2. LỚP BẢO HIỂM (FALLBACK): Nếu RAM rỗng, cầu cứu Database
    col = _get_forms_col()
    if col is not None:
        doc = await col.find_one({"guild_id": gid, "embed_name": name})
        if doc:
            # Đồng bộ ngược dữ liệu vừa tìm được lên RAM để các lần sau chạy xé gió
            if gid not in FORMS_CACHE:
                FORMS_CACHE[gid] = {}
            FORMS_CACHE[gid][name] = doc
            return doc
            
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
        payload = {
            "form_title": title,
            "log_channel_id": log_id,
            "show_thumbnail": thumbnail
        }
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": payload},
            upsert=True
        )
        
        # [ĐỒNG BỘ RAM NÓNG LẬP TỨC] Chống lệch mạch hiển thị
        if gid not in FORMS_CACHE:
            FORMS_CACHE[gid] = {}
        if name not in FORMS_CACHE[gid]:
            FORMS_CACHE[gid][name] = {"guild_id": gid, "embed_name": name, "fields": {}}
            
        FORMS_CACHE[gid][name].update(payload)
        return True
    return False

async def update_form_field(guild_id: int, embed_name: str, slot: int, label: str, placeholder: str, required: bool):
    """Cập nhật dữ liệu chi tiết cho từng ô nhập liệu (Field Slot)."""
    if not embed_name: return False
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        field_data = {
            "label": label,
            "placeholder": placeholder,
            "required": required
        }
        # Cập nhật chính xác vào nested object 'fields' của Form
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": {f"fields.{slot}": field_data}},
            upsert=True
        )
        
        # [ĐỒNG BỘ RAM NÓNG LẬP TỨC] Nạp đè chính xác ô nhập liệu vào bộ nhớ đệm
        if gid not in FORMS_CACHE:
            FORMS_CACHE[gid] = {}
        if name not in FORMS_CACHE[gid]:
            FORMS_CACHE[gid][name] = {"guild_id": gid, "embed_name": name, "fields": {}}
            
        if "fields" not in FORMS_CACHE[gid][name]:
            FORMS_CACHE[gid][name]["fields"] = {}
            
        FORMS_CACHE[gid][name]["fields"][str(slot)] = field_data
        return True
    return False

# ==========================================
# INTERACTION LOGIC (GIA CỐ KHOẢNG CÁCH)
# ==========================================

class YiyiFormModal(discord.ui.Modal):
    """Lớp giao diện bảng nhập liệu hiện lên khi người dùng bấm nút."""
    def __init__(self, title, fields_data, log_channel_id, show_thumbnail):
        # [ANTI-CRASH] Gọt tiêu đề xuống tối đa 45 ký tự theo luật Discord
        safe_title = title[:45] if title else "Biểu mẫu Yiyi"
        super().__init__(title=safe_title)
        
        self.log_channel_id = log_channel_id
        self.show_thumbnail = show_thumbnail
        self.inputs = {}

        # Sắp xếp các ô nhập liệu theo đúng thứ tự slot (1 -> 5)
        sorted_slots = sorted(fields_data.keys(), key=lambda x: int(x))

        for slot in sorted_slots:
            data = fields_data[slot]
            
            # [ANTI-CRASH] Gọt nhãn và placeholder để lách giới hạn API Discord
            safe_label = data['label'][:45]
            safe_placeholder = data['placeholder'][:100] if data.get('placeholder') else "Nhập nội dung..."
            
            text_input = discord.ui.TextInput(
                label=safe_label,
                placeholder=safe_placeholder,
                required=data['required'],
                style=discord.TextStyle.paragraph if len(safe_label) > 15 else discord.TextStyle.short
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
        
        # Hiện Avatar làm thumbnail ở góc trên bên phải theo chuẩn kiến trúc
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
