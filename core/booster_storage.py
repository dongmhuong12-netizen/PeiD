import asyncio
import copy
from core.cache_manager import get_raw, mark_dirty

FILE_KEY = "booster_levels"

def _normalize_levels(levels: list):
    """Chuẩn hóa dữ liệu Level: Xử lý an toàn các giá trị None/Rác"""
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        if not isinstance(lvl, dict): continue
        
        role_id = lvl.get("role")
        days = lvl.get("days")
        
        # Chỉ lấy những level có ID hợp lệ
        if role_id:
            try:
                normalized.append({
                    "role": int(role_id), # Lưu dạng INT để đồng bộ với discord.py
                    "days": int(days) if days is not None else 0
                })
            except (ValueError, TypeError):
                continue
    
    # Sắp xếp tăng dần theo ngày
    return sorted(normalized, key=lambda x: x["days"])

async def get_guild_config(guild_id: int):
    """Lấy cấu hình an toàn, chống treo Bot"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    # Lấy config gốc hoặc tạo mới
    raw_config = db.get(guild_id_str, {})
    if not isinstance(raw_config, dict): raw_config = {}

    # Khởi tạo Schema chuẩn
    config = {
        "booster_role": raw_config.get("booster_role"),
        "levels": raw_config.get("levels", [])
    }

    # Hỗ trợ Migrate dữ liệu cũ nếu là Dictionary
    if isinstance(config["levels"], dict):
        new_levels = []
        for _, v in config["levels"].items():
            if isinstance(v, dict):
                new_levels.append(v)
        config["levels"] = new_levels

    # Luôn chuẩn hóa trước khi đưa vào View
    config["levels"] = _normalize_levels(config["levels"])
    
    # Đảm bảo booster_role là Int hoặc None
    if config["booster_role"]:
        try: config["booster_role"] = int(config["booster_role"])
        except: config["booster_role"] = None

    return copy.deepcopy(config)

async def save_guild_config(guild_id: int, config: dict):
    """Ghi dữ liệu sạch xuống Cache"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    db[guild_id_str] = {
        "booster_role": int(config["booster_role"]) if config.get("booster_role") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    mark_dirty(FILE_KEY)

# --- Interface (Giữ nguyên tên hàm để không hỏng UI) ---
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
