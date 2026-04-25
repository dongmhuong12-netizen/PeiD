import asyncio
import copy
from core.cache_manager import get_raw, mark_dirty

# Key đồng bộ với hệ thống Booster
FILE_KEY = "booster_levels"

# =========================
# INTERNAL HELPERS
# =========================

def _normalize_levels(levels: list):
    """
    Chuẩn hóa dữ liệu Level: Xử lý an toàn các giá trị None/Rác.
    GIỮ NGUYÊN LOGIC CỦA NGUYỆT: Lọc role hợp lệ và sắp xếp tăng dần.
    """
    if not isinstance(levels, list):
        return []
        
    normalized = []
    for lvl in levels:
        if not isinstance(lvl, dict): continue
        
        role_id = lvl.get("role")
        days = lvl.get("days")
        
        # Chỉ lấy những level có ID hợp lệ và ép kiểu Int để Discord.py dễ dùng
        if role_id:
            try:
                normalized.append({
                    "role": int(role_id), 
                    "days": int(days) if days is not None else 0
                })
            except (ValueError, TypeError):
                continue
    
    # Sắp xếp tăng dần theo ngày để Booster Engine (Step 15) duyệt nhanh hơn
    return sorted(normalized, key=lambda x: x["days"])

# =========================
# PUBLIC API (CẤU TRÚC ATOMIC)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy cấu hình an toàn, hỗ trợ tự phục hồi và Migrate dữ liệu.
    BẢO TOÀN 100% LOGIC CỦA NGUYỆT.
    """
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)
    
    # Lấy config gốc từ RAM (Source of Truth)
    raw_config = db.get(guild_id_str, {})
    if not isinstance(raw_config, dict): raw_config = {}

    # Khởi tạo Schema chuẩn (Bền vững 100k+)
    config = {
        "booster_role": raw_config.get("booster_role"),
        "levels": raw_config.get("levels", [])
    }

    # LOGIC MIGRATE CỦA NGUYỆT: Chuyển từ Dict sang List nếu dữ liệu cũ còn sót lại
    if isinstance(config["levels"], dict):
        new_levels = []
        for _, v in config["levels"].items():
            if isinstance(v, dict):
                new_levels.append(v)
        config["levels"] = new_levels

    # Luôn chuẩn hóa trước khi trả về để đảm bảo tính nhất quán
    config["levels"] = _normalize_levels(config["levels"])
    
    # Đảm bảo booster_role là Int (Discord.py ID Standard)
    if config["booster_role"]:
        try: config["booster_role"] = int(config["booster_role"])
        except: config["booster_role"] = None

    # TRẢ VỀ DEEPCOPY: Để các View (như BoosterLevelView) không sửa hỏng dữ liệu gốc
    return copy.deepcopy(config)

async def save_guild_config(guild_id: int, config: dict):
    """Ghi dữ liệu sạch xuống Cache và kích hoạt hàng đợi ghi đĩa ngầm"""
    db = get_raw(FILE_KEY)
    guild_id_str = str(guild_id)

    # Đảm bảo dữ liệu được làm sạch trước khi ghi xuống Disk
    db[guild_id_str] = {
        "booster_role": int(config["booster_role"]) if config.get("booster_role") else None,
        "levels": _normalize_levels(config.get("levels", []))
    }
    
    # Đánh dấu dữ liệu đã thay đổi để CacheManager tự động lưu sau 5s
    mark_dirty(FILE_KEY)
    print(f"[STORAGE] Booster config saved for Guild {guild_id_str}", flush=True)

# =========================
# INTERFACE (KHÔNG THAY ĐỔI TÊN HÀM)
# =========================

async def set_booster_role(guild_id: int, role_id: int):
    """Cập nhật nhanh Booster Role định danh"""
    config = await get_guild_config(guild_id)
    config["booster_role"] = role_id
    await save_guild_config(guild_id, config)

async def get_levels(guild_id: int):
    """Lấy danh sách Level đã sắp xếp"""
    config = await get_guild_config(guild_id)
    return config.get("levels", [])

async def save_levels(guild_id: int, levels: list):
    """Lưu danh sách Level mới"""
    config = await get_guild_config(guild_id)
    config["levels"] = levels
    await save_guild_config(guild_id, config)
