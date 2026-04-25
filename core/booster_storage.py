import copy
from core.cache_manager import get_raw, mark_dirty, save # Thêm save để ép lưu

# Key đồng bộ với hệ thống Booster
FILE_KEY = "booster_levels"

# =========================
# INTERNAL HELPERS
# =========================

def _normalize_levels(levels: list):
    """
    Chuẩn hóa dữ liệu Level: Lọc role hợp lệ và sắp xếp tăng dần.
    """
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        if not isinstance(lvl, dict): continue
        
        role_id = lvl.get("role")
        days = lvl.get("days")
        
        if role_id:
            try:
                normalized.append({
                    "role": str(role_id), # Lưu ID dạng String để tránh lỗi JSON
                    "days": int(days) if days is not None else 0
                })
            except (ValueError, TypeError):
                continue
    
    return sorted(normalized, key=lambda x: x["days"])

# =========================
# PUBLIC API (CẤU TRÚC BỀN VỮNG)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy toàn bộ cấu hình server, đảm bảo không làm mất các key phụ (channel, embed...).
    """
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    # Lấy toàn bộ dict hiện có thay vì chỉ lấy 2 key
    config = db.get(guild_id_str, {})
    if not isinstance(config, dict): config = {}

    # Đảm bảo các mảng cốt lõi luôn tồn tại và đúng định dạng
    if "levels" not in config or not isinstance(config["levels"], list):
        config["levels"] = []
    
    # Trả về bản sao để an toàn
    return copy.deepcopy(config)

async def save_guild_config(guild_id: int, config: dict):
    """
    Lưu và ÉP GHI xuống đĩa ngay lập tức để chống Render restart.
    """
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    # Cập nhật toàn bộ config vào RAM
    # Chúng ta lưu cả channel, message, embed và levels vào đây
    if "levels" in config:
        config["levels"] = _normalize_levels(config["levels"])
        
    db[guild_id_str] = config
    
    # 1. Đánh dấu bẩn
    mark_dirty(FILE_KEY)
    
    # 2. ÉP LƯU NGAY LẬP TỨC (Nút thắt dứt điểm mất trí nhớ)
    await save(FILE_KEY)
    
    print(f"[STORAGE] Đã đóng đinh cấu hình Booster cho Guild {guild_id_str}", flush=True)

# =========================
# INTERFACE (DÀNH CHO UI & ENGINE)
# =========================

async def set_booster_role(guild_id: int, role_id: int):
    config = await get_guild_config(guild_id)
    config["booster_role"] = role_id
    await save_guild_config(guild_id, config)

async def get_levels(guild_id: int):
    config = await get_guild_config(guild_id)
    return config.get("levels", [])

async def save_levels(guild_id: int, levels: list):
    config = await get_guild_config(guild_id)
    config["levels"] = levels
    await save_guild_config(guild_id, config)
