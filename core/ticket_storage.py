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
    
    if db is not None:
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
    
    if db is not None:
        # Đảm bảo ghi đè chính xác vào ngăn 'settings' của module ticket
        await db.configs.update_one(
            {"guild_id": gid, "module": "ticket"},
            {"$set": {"settings": config_data}},
            upsert=True
        )
        return True
    return False

# =============================
# STAFF MANAGEMENT (BỔ SUNG LŨY TIẾN)
# =============================

async def add_ticket_staff(guild_id: int, role_ids: list):
    """
    [ATK - INCREMENTAL] 
    Thêm role staff bằng toán tử $addToSet.
    Đảm bảo: Thêm là đắp thêm, không bao giờ làm mất dữ liệu cũ.
    """
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db is not None:
        # $addToSet + $each: Thêm nhiều phần tử vào mảng, tự động loại bỏ trùng lặp
        await db.configs.update_one(
            {"guild_id": gid, "module": "ticket"},
            {"$addToSet": {"settings.staff_roles": {"$each": role_ids}}},
            upsert=True
        )
        return True
    return False

async def remove_ticket_staff(guild_id: int, role_ids: list):
    """
    [DEF - CLEANUP] 
    Xóa role staff bằng toán tử $pullAll.
    Đảm bảo: Chỉ nhổ đúng những ID role được chỉ định, giữ nguyên các role khác.
    """
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db is not None:
        # $pullAll: Xóa toàn bộ các giá trị có trong danh sách role_ids khỏi mảng
        await db.configs.update_one(
            {"guild_id": gid, "module": "ticket"},
            {"$pullAll": {"settings.staff_roles": role_ids}}
        )
        return True
    return False
