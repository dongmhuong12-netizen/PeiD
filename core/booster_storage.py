import copy
from core.cache_manager import get_raw, mark_dirty

# Key đồng bộ với hệ thống Booster
FILE_KEY = "booster_levels"

# =========================
# INTERNAL HELPERS
# =========================

def _normalize_levels(levels: list):
    """
    Chuẩn hóa dữ liệu Level: Lọc role hợp lệ và sắp xếp tăng dần.
    BẢO TOÀN 100% LOGIC CỦA NGUYỆT.
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
                    "role": int(role_id), 
                    "days": int(days) if days is not None else 0
                })
            except (ValueError, TypeError):
                continue
    
    # Sắp xếp để Engine có thể thực hiện Early Break (Tối ưu CPU)
    return sorted(normalized, key=lambda x: x["days"])

# =========================
# PUBLIC API (CẤU TRÚC BỀN VỮNG)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy cấu hình an toàn, hỗ trợ Migrate và bảo vệ RAM gốc.
    """
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    raw_config = db.get(guild_id_str, {})
    if not isinstance(raw_config, dict): raw_config = {}

    config = {
        "booster_role": raw_config.get("booster_role"),
        "levels": raw_config.get("levels", [])
    }

    # LOGIC MIGRATE: Chuyển đổi dữ liệu cũ nếu Admin dùng format cũ
    if isinstance(config["levels"], dict):
        new_levels = [v for k, v in config["levels"].items() if isinstance(v, dict)]
        config["levels"] = new_levels

    # Chuẩn hóa để đảm bảo tính nhất quán của ID và Thứ tự
    config["levels"] = _normalize_levels(config["levels"])
    
    if config["booster_role"]:
        try: config["booster_role"] = int(config["booster_role"])
        except: config["booster_role"] = None

    # Trả về bản sao để UI/Engine không vô tình sửa hỏng RAM gốc
    return copy.deepcopy(config)

async def save_guild_config(guild_id: int, config: dict):
    """Lọc dữ liệu sạch và kích hoạt hàng đợi ghi đĩa ngầm (CacheManager)"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    db[guild_id_str] = {
        "booster_role": int(config["booster_role"]) if config.get("booster_role") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    
    mark_dirty(FILE_KEY)

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
