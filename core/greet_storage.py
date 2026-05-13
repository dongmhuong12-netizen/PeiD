import copy
import asyncio
# [CẤY MỚI] Kết nối với não bộ bot.db thông qua State
from core.state import State

# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
# from core.cache_manager import get_raw, mark_dirty, update

# Khởi tạo một bộ đệm RAM để duy trì vận hành Stateless
_internal_greet_cache = {}

# =========================
# INTERNAL HELPERS
# =========================

def _get_cache():
    """
    Lấy dữ liệu trực tiếp từ RAM. 
    Tự động sửa lỗi nếu cấu hình bị hỏng (Self-healing).
    """
    return _internal_greet_cache

# =========================
# PUBLIC API (STATLESS + CLOUD SYNC)
# =========================

async def get_guild_config(guild_id: int):
    """
    Lấy toàn bộ cấu hình Greet/Leave/Wellcome của server.
    Logic: RAM first, nạp từ Cloud nếu RAM trống sau khi reboot.
    """
    cache = _get_cache()
    gid = str(guild_id)
    
    # [CẤY MỚI] Tự phục hồi dữ liệu từ Cloud Atlas nếu RAM hụt
    if gid not in cache and hasattr(State.bot, "db"):
        doc = await State.bot.db.configs.find_one({
            "guild_id": gid, 
            "module": "greet_leave"
        })
        if doc:
            cache[gid] = doc.get("settings", {})

    config = cache.get(gid, {})
    
    # Bảo vệ RAM gốc và đảm bảo cấu trúc 3 nhánh luôn sẵn sàng (Industrial Grade)
    return copy.deepcopy(config) if config else {"greet": {}, "leave": {}, "wellcome": {}}


async def update_guild_config(guild_id: int, section: str, key: str, value):
    """
    Cập nhật cấu hình vào bộ nhớ RAM và đồng bộ tức thì lên Cloud Atlas.
    """
    cache = _get_cache()
    gid = str(guild_id)

    # Khởi tạo không gian lưu trữ cho Guild nếu chưa có (mở rộng thêm wellcome)
    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {"greet": {}, "leave": {}, "wellcome": {}}

    if section not in cache[gid] or not isinstance(cache[gid][section], dict):
        cache[gid][section] = {}

    # Ghi trực tiếp vào RAM (Source of Truth)
    cache[gid][section][key] = value

    # [CẤY MỚI] Đồng bộ Cloud Atlas vào ngăn 'configs'
    if hasattr(State.bot, "db"):
        await State.bot.db.configs.update_one(
            {"guild_id": gid, "module": "greet_leave"},
            {"$set": {f"settings.{section}.{key}": value}},
            upsert=True
        )

    print(f"[STORAGE] Updated {section}.{key} for Guild {gid} (Cloud Synced)", flush=True)


async def get_section(guild_id: int, section: str):
    """Lấy riêng phần cấu hình Greet/Leave/Wellcome (Bản sao an toàn)"""
    config = await get_guild_config(guild_id)
    return config.get(section, {})
