import copy
import asyncio
from collections import defaultdict
from core.cache_manager import get_raw, mark_dirty, save, update

# Key đồng bộ với hệ thống Booster
FILE_KEY = "booster_levels"

# [VÁ LỖI] Khóa theo Guild để tránh Race Condition khi Read-Modify-Write
_guild_locks = defaultdict(asyncio.Lock)

# =========================
# INTERNAL HELPERS
# =========================

def _get_cache():
    """
    Lấy reference gốc từ RAM. Tự sửa lỗi định dạng.
    """
    cache = get_raw(FILE_KEY)
    if not isinstance(cache, dict):
        print(f"[STORAGE WARNING] Cache '{FILE_KEY}' bị hỏng. Đang reset...", flush=True)
        cache = {}
        update(FILE_KEY, cache)
        mark_dirty(FILE_KEY)
    return cache

# =========================
# PUBLIC API (CẤU TRÚC BỀN VỮNG)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy toàn bộ cấu hình server (role, channel, message...).
    Đã gỡ bỏ hoàn toàn logic liên quan đến mốc levels.
    """
    db = _get_cache()
    guild_id_str = str(guild_id)
    
    config = db.get(guild_id_str, {})
    if not isinstance(config, dict): config = {}

    # [VÁ LỖI NỘI SOI]: Đảm bảo các ID luôn là string/int sạch để Engine không bị crash
    # Purge sạch các data rác từ hệ thống level cũ nếu còn sót lại
    clean_config = {
        "booster_role": config.get("booster_role"),
        "channel": config.get("channel"),
        "message": config.get("message"),
        "embed": config.get("embed")
    }
    
    # Trả về bản sao để an toàn cho RAM gốc
    return copy.deepcopy(clean_config)

async def save_guild_config(guild_id: int, config: dict):
    """
    Lưu cấu hình booster gốc vào bộ nhớ.
    """
    db = _get_cache()
    guild_id_str = str(guild_id)
        
    db[guild_id_str] = config
    
    # Đánh dấu bẩn để CacheManager tự động lưu ngầm định kỳ
    mark_dirty(FILE_KEY)
    
    print(f"[STORAGE] **yiyi** đã ghi nhận cấu hình Booster cho Guild {guild_id_str}", flush=True)

# =========================
# INTERFACE (DÀNH CHO ENGINE)
# =========================

async def set_booster_role(guild_id: int, role_id: int):
    # [VÁ LỖI] Dùng Lock để đảm bảo quá trình Đọc-Sửa-Ghi không bị xen ngang
    lock = _guild_locks[guild_id]
    async with lock:
        config = await get_guild_config(guild_id)
        config["booster_role"] = role_id
        await save_guild_config(guild_id, config)
    if guild_id in _guild_locks and not lock.locked(): _guild_locks.pop(guild_id, None)
