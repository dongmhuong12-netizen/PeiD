from core.state import State

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
