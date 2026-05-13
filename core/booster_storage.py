import copy
import asyncio
from collections import defaultdict

# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
# from core.cache_manager import get_raw, mark_dirty, save, update

# Khởi tạo một bộ đệm RAM để duy trì vận hành (Stateless)
_internal_booster_storage = {}

# [VÁ LỖI] Khóa theo Guild để tránh Race Condition khi Read-Modify-Write
_guild_locks = defaultdict(asyncio.Lock)

# =========================
# INTERNAL HELPERS
# =========================

def _get_cache():
    """
    Lấy reference gốc từ RAM. Tự sửa lỗi định dạng.
    """
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Chuyển từ file cục bộ sang bộ đệm RAM
    return _internal_booster_storage

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
    Lưu cấu hình booster gốc vào bộ nhớ RAM.
    """
    db = _get_cache()
    guild_id_str = str(guild_id)
        
    db[guild_id_str] = config
    
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ mark_dirty (không còn ghi đĩa cục bộ)
    
    print(f"[STORAGE] **yiyi** đã ghi nhận cấu hình Booster cho Guild {guild_id_str} (Stateless Mode)", flush=True)

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
    if guild_id in _guild_locks and not lock.locked(): 
        _guild_locks.pop(guild_id, None)
