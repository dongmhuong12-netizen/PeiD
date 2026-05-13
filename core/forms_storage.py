from core.state import State

async def get_form_config(guild_id: int, embed_name: str):
    """Lấy cấu hình Form cụ thể gắn với định danh Embed."""
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db:
        # Truy vấn theo embed_name để hỗ trợ nhiều form khác nhau trong 1 server
        doc = await db.forms.find_one({"guild_id": gid, "embed_name": embed_name.lower()})
        return doc if doc else None
    return None

async def update_form_base(guild_id: int, embed_name: str, title: str, log_id: str, thumbnail: bool):
    """Cập nhật thông tin khung (Base) của Form."""
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db:
        await db.forms.update_one(
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
    db = getattr(State.bot, "db", None)
    if db:
        # Cập nhật chính xác vào nested object 'fields' của Form
        await db.forms.update_one(
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
