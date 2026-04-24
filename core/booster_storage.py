import asyncio
import copy
from core.cache_manager import get_raw, mark_dirty

# Sử dụng Key đồng bộ để nạp vào hệ thống Cache tập trung
FILE_KEY = "booster_levels"

# ==============================
# NORMALIZE LEVELS
# ==============================

def _normalize_levels(levels: list):
    """Chuẩn hóa dữ liệu Level: Sắp xếp theo ngày tăng dần để logic gán Role luôn chính xác"""
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        role_id = lvl.get("role")
        days = lvl.get("days")
        if role_id is not None:
            normalized.append({
                "role": str(role_id), 
                "days": int(days) if days is not None else 0
            })
    
    # TIÊU CHUẨN 100K+: Tự động sắp xếp theo ngày để hệ thống gán role không bị nhầm lẫn
    return sorted(normalized, key=lambda x: x["days"])


# ==============================
# GET CONFIG
# ==============================

async def get_guild_config(guild_id: int):
    """Lấy cấu hình Booster/Level trực tiếp từ RAM (O(1) Speed)"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    config = db.get(guild_id_str, {})

    # Khởi tạo cấu hình mặc định nếu chưa có
    if not config:
        config = {
            "booster_role": None,
            "levels": []
        }

    # --- Logic Migrate (Đảm bảo tương thích dữ liệu cũ) ---
    levels = config.get("levels")
    if isinstance(levels, dict):
        new_levels = []
        for _, value in sorted(levels.items(), key=lambda x: int(x[0])):
            new_levels.append({
                "role": value.get("role"),
                "days": value.get("days")
            })
        config["levels"] = new_levels
        db[guild_id_str] = config
        mark_dirty(FILE_KEY)

    # Đảm bảo schema sạch sẽ
    config.setdefault("booster_role", None)
    if not isinstance(config.get("levels"), list):
        config["levels"] = []

    config["levels"] = _normalize_levels(config["levels"])
    
    # Trả về bản sao để bảo vệ RAM gốc
    return copy.deepcopy(config)


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):
    """Lưu cấu hình vào Cache và đánh dấu để ghi xuống Disk ngầm"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    # Chỉ lưu những thông tin cốt lõi về Role và Level
    db[guild_id_str] = {
        "booster_role": str(config.get("booster_role")) if config.get("booster_role") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    
    mark_dirty(FILE_KEY)


# ==============================
# INTERFACE (Giữ nguyên để tương thích 100%)
# ==============================

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


async def clear_levels(guild_id: int):
    await save_guild_config(guild_id, {"levels": []})
