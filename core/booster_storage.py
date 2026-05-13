import copy
import asyncio
from collections import defaultdict
# [CẤY MỚI] Nạp State để truy cập vào bot.db
from core.state import State

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
    return _internal_booster_storage

# =========================
# PUBLIC API (CẤU TRÚC BỀN VỮNG)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy toàn bộ cấu hình server (role, channel, message...).
    Logic: Ưu tiên RAM (Max Ping). Nếu RAM hụt (do reboot), nạp từ MongoDB.
    """
    db = _get_cache()
    guild_id_str = str(guild_id)
    
    # [CẤY MỚI] Cơ chế nạp từ MongoDB nếu RAM trống (Self-healing RAM)
    if guild_id_str not in db and hasattr(State.bot, "db"):
        doc = await State.bot.db.configs.find_one({
            "guild_id": guild_id_str, 
            "module": "booster"
        })
        if doc:
            db[guild_id_str] = doc.get("settings", {})

    config = db.get(guild_id_str, {})
    if not isinstance(config, dict): config = {}

    # [VÁ LỖI NỘI SOI]: Đảm bảo các ID luôn là string/int sạch để Engine không bị crash
    clean_config = {
        "booster_role": config.get("booster_role"),
        "channel": config.get("channel"),
        "message": config.get("message"),
        "embed": config.get("embed")
    }
    
    return copy.deepcopy(clean_config)

async def save_guild_config(guild_id: int, config: dict):
    """
    Lưu cấu hình booster gốc vào bộ nhớ RAM + Đồng bộ Cloud.
    """
    db = _get_cache()
    guild_id_str = str(guild_id)
        
    db[guild_id_str] = config
    
    # [CẤY MỚI] Đồng bộ lên Cloud Atlas (Ngăn configs)
    if hasattr(State.bot, "db"):
        await State.bot.db.configs.update_one(
            {"guild_id": guild_id_str, "module": "booster"},
            {"$set": {"settings": config}},
            upsert=True
        )
    
    print(f"[STORAGE] **yiyi** đã ghi nhận cấu hình Booster cho Guild {guild_id_str} (Cloud Synced)", flush=True)

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
    # Tự dọn dẹp lock để tiết kiệm tài nguyên (Industrial Standard)
    if guild_id in _guild_locks and not lock.locked(): 
        _guild_locks.pop(guild_id, None)

async def set_booster_channel(guild_id: int, channel_id: int):
    """Cập nhật kênh thông báo Booster"""
    lock = _guild_locks[guild_id]
    async with lock:
        config = await get_guild_config(guild_id)
        config["channel"] = channel_id
        await save_guild_config(guild_id, config)
    if guild_id in _guild_locks and not lock.locked(): 
        _guild_locks.pop(guild_id, None)

async def set_booster_message(guild_id: int, message: str):
    """Cập nhật nội dung tin nhắn Booster"""
    lock = _guild_locks[guild_id]
    async with lock:
        config = await get_guild_config(guild_id)
        config["message"] = message
        await save_guild_config(guild_id, config)
    if guild_id in _guild_locks and not lock.locked(): 
        _guild_locks.pop(guild_id, None)

async def set_booster_embed(guild_id: int, embed_name: str):
    """Cập nhật mẫu Embed cho Booster"""
    lock = _guild_locks[guild_id]
    async with lock:
        config = await get_guild_config(guild_id)
        config["embed"] = embed_name
        await save_guild_config(guild_id, config)
    if guild_id in _guild_locks and not lock.locked(): 
        _guild_locks.pop(guild_id, None)
