import asyncio
from core.cache_manager import get_raw, mark_dirty

# Sử dụng Key đồng bộ để nạp vào hệ thống Cache tập trung
FILE_KEY = "booster_levels"

# ==============================
# NORMALIZE LEVELS
# ==============================

def _normalize_levels(levels: list):
    """Giữ nguyên logic chuẩn hóa của Nguyệt nhưng đảm bảo kiểu dữ liệu sạch"""
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        role_id = lvl.get("role")
        days = lvl.get("days")
        if role_id:
            normalized.append({
                "role": str(role_id), # Ép về str để đồng bộ ID Discord
                "days": int(days) if days is not None else 0
            })
    return normalized


# ==============================
# GET CONFIG
# ==============================

async def get_guild_config(guild_id: int):
    """Lấy cấu hình trực tiếp từ RAM (O(1) Speed)"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    config = db.get(guild_id_str, {})
    
    # Trả về cấu hình mặc định nếu chưa có dữ liệu trong Cache
    return {
        "booster_role": config.get("booster_role"),
        "channel": config.get("channel"),
        "levels": _normalize_levels(config.get("levels", []))
    }


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):
    """Lưu cấu hình vào Cache và đánh dấu Dirty để lưu Disk sau"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    # Chuẩn hóa lại dữ liệu trước khi lưu vào Cache
    db[guild_id_str] = {
        "booster_role": str(config.get("booster_role")) if config.get("booster_role") else None,
        "channel": str(config.get("channel")) if config.get("channel") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    
    # Đánh dấu dữ liệu đã thay đổi để Cache Manager tự động ghi xuống file
    mark_dirty(FILE_KEY)


# ==============================
# SHORTHAND METHODS (Giữ nguyên Interface cũ)
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
    config = await get_guild_config(guild_id)
    config["levels"] = []
    await save_guild_config(guild_id, config)
