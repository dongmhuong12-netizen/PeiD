import asyncio
from core.cache_manager import get_raw, mark_dirty

# Sử dụng Key đồng bộ để nạp vào hệ thống Cache tập trung
FILE_KEY = "booster_levels"

# ==============================
# NORMALIZE LEVELS
# ==============================

def _normalize_levels(levels: list):
    """Giữ nguyên logic chuẩn hóa nhưng đảm bảo kiểu dữ liệu sạch cho quy mô lớn"""
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        role_id = lvl.get("role")
        days = lvl.get("days")
        if role_id is not None:
            normalized.append({
                "role": str(role_id), # Ép về str để tránh lỗi so sánh ID Discord
                "days": int(days) if days is not None else 0
            })
    return normalized


# ==============================
# GET CONFIG
# ==============================

async def get_guild_config(guild_id: int):
    """Lấy cấu hình Booster/Level trực tiếp từ RAM (O(1) Speed)"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    # Lấy dữ liệu từ cache, nếu không có trả về dict trống
    config = db.get(guild_id_str, {})

    if not config:
        return {
            "booster_role": None,
            "channel": None,
            "booster_channel": None, # Thêm để hỗ trợ hệ booster thường độc lập
            "levels": []
        }

    # --- Logic Migrate (Giữ nguyên logic của Nguyệt nhưng chạy trên RAM) ---
    levels = config.get("levels")
    if isinstance(levels, dict):
        new_levels = []
        for _, value in sorted(
            levels.items(),
            key=lambda x: int(x[0])
        ):
            new_levels.append({
                "role": value.get("role"),
                "days": value.get("days")
            })

        config["levels"] = _normalize_levels(new_levels)
        db[guild_id_str] = config
        mark_dirty(FILE_KEY)

    # Đảm bảo đầy đủ các key cần thiết
    if "booster_role" not in config:
        config["booster_role"] = None
    if "channel" not in config:
        config["channel"] = None
    if "booster_channel" not in config:
        config["booster_channel"] = None
    if not isinstance(config.get("levels"), list):
        config["levels"] = []

    config["levels"] = _normalize_levels(config["levels"])
    return config


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):
    """Lưu cấu hình vào Cache và đánh dấu để hệ thống Core tự động ghi xuống Disk"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    # Chuẩn hóa dữ liệu trước khi nạp vào Cache
    db[guild_id_str] = {
        "booster_role": str(config.get("booster_role")) if config.get("booster_role") else None,
        "channel": str(config.get("channel")) if config.get("channel") else None,
        "booster_channel": str(config.get("booster_channel")) if config.get("booster_channel") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    
    mark_dirty(FILE_KEY)


# ==============================
# SHORTHAND METHODS (Interface giữ nguyên 100% để tương thích file khác)
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
    config["levels"] = _normalize_levels(levels)
    await save_guild_config(guild_id, config)


async def clear_levels(guild_id: int):
    config = await get_guild_config(guild_id)
    config["levels"] = []
    await save_guild_config(guild_id, config)
