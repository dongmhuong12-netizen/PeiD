from core.state import State

async def get_ticket_config(guild_id: int):
    """
    [DEF - INDUSTRIAL VALIDATION]
    Truy xuất cấu hình Ticket từ Cloud Atlas.
    Đảm bảo luôn trả về một dictionary (tránh lỗi NoneType ở tầng UI).
    """
    gid = str(guild_id)
    # Truy xuất database thông qua State (Tiêu chuẩn 100k+)
    db = getattr(State.bot, "db", None)
    
    if db:
        # [NGUỒN SỰ THẬT] Dữ liệu nằm trong collection 'configs'
        doc = await db.configs.find_one({"guild_id": gid, "module": "ticket"})
        if doc and "settings" in doc:
            return doc["settings"]
            
    # Trả về dict trống thay vì None để các lệnh calling không bị crash
    return {}

async def update_ticket_config(guild_id: int, config_data: dict):
    """
    [ATK - ATOMIC SYNC]
    Đồng bộ cấu hình Ticket lên Cloud Atlas.
    Sử dụng upsert để khởi tạo hoặc cập nhật mạch dữ liệu trong 1 nốt nhạc.
    """
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    
    if db:
        # Đảm bảo ghi đè chính xác vào ngăn 'settings' của module ticket
        await db.configs.update_one(
            {"guild_id": gid, "module": "ticket"},
            {"$set": {"settings": config_data}},
            upsert=True
        )
        return True
    return False
