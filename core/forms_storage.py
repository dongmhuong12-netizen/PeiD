from core.state import State

def _get_forms_col():
    """
    [BỘ LỌC THÔNG MINH YIYI]
    Tự động tìm đường vào collection 'forms' mà không cần sếp phải khai báo
    thuộc tính .forms ở class MongoDB gốc.
    """
    db = getattr(State.bot, "db", None)
    if not db: return None
    
    # 1. Nếu sau này sếp rảnh khai báo sẵn .forms thì dùng luôn
    if hasattr(db, "forms"):
        return db.forms
        
    # 2. Vòng qua lưng: Mượn engine gốc (thường nằm ở .db)
    if hasattr(db, "db"):
        return db.db["forms"]
        
    # 3. Kế hoạch Z: Mượn đường ống của embeds để chọc vào Database
    if hasattr(db, "embeds"):
        return db.embeds.database["forms"]
        
    return None

async def get_form_config(guild_id: int, embed_name: str):
    """Lấy cấu hình Form cụ thể gắn với định danh Embed."""
    gid = str(guild_id)
    col = _get_forms_col()
    
    if col is not None:
        # Truy vấn theo embed_name để hỗ trợ nhiều form khác nhau trong 1 server
        doc = await col.find_one({"guild_id": gid, "embed_name": embed_name.lower()})
        return doc if doc else None
    return None

async def update_form_base(guild_id: int, embed_name: str, title: str, log_id: str, thumbnail: bool):
    """Cập nhật thông tin khung (Base) của Form."""
    gid = str(guild_id)
    col = _get_forms_col()
    
    if col is not None:
        await col.update_one(
            {"guild_id": gid, "embed_name": embed_name.lower()},
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
    gid = str(guild_id)
    col = _get_forms_col()
    
    if col is not None:
        # Cập nhật chính xác vào nested object 'fields' của Form
        await col.update_one(
            {"guild_id": gid, "embed_name": embed_name.lower()},
            {"$set": {f"fields.{slot}": {
                "label": label,
                "placeholder": placeholder,
                "required": required
            }}},
            upsert=True
        )
        return True
    return False
