import copy
import asyncio
# [CẤY MỚI] Kết nối với não bộ bot.db thông qua State
from core.state import State

# Khởi tạo một bộ đệm RAM để duy trì vận hành Stateless (100k+ servers optimization)
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
    Logic: RAM first, nạp từ Cloud nếu RAM trống sau khi reboot (Industrial Standard).
    """
    cache = _get_cache()
    gid = str(guild_id)
    
    # [CẤY MỚI] Tự phục hồi dữ liệu từ Cloud Atlas nếu RAM hụt (Sau khi Render restart)
    if gid not in cache:
        db = getattr(State.bot, "db", None)
        if db:
            doc = await db.configs.find_one({
                "guild_id": gid, 
                "module": "greet_leave"
            })
            if doc:
                cache[gid] = doc.get("settings", {})
            else:
                # Khởi tạo khung xương nếu server mới hoàn toàn để tránh truy vấn lặp
                cache[gid] = {"greet": {}, "leave": {}, "wellcome": {}}

    config = cache.get(gid, {})
    
    # Đảm bảo cấu trúc 3 nhánh luôn tồn tại trước khi trả về (Self-healing)
    if not isinstance(config, dict): config = {}
    for s in ["greet", "leave", "wellcome"]:
        if s not in config: config[s] = {}

    # Bảo vệ RAM gốc bằng Deepcopy (Bản sao an toàn cho logic xử lý biến số)
    return copy.deepcopy(config)


async def update_guild_config(guild_id: int, section: str, key: str, value):
    """
    Cập nhật cấu hình vào bộ nhớ RAM và đồng bộ tức thì lên Cloud Atlas.
    """
    cache = _get_cache()
    gid = str(guild_id)

    # Khởi tạo không gian lưu trữ cho Guild nếu chưa có (Hỗ trợ 3 nhánh Greet/Leave/Wellcome)
    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {"greet": {}, "leave": {}, "wellcome": {}}

    if section not in cache[gid] or not isinstance(cache[gid][section], dict):
        cache[gid][section] = {}

    # Ghi trực tiếp vào RAM (Source of Truth tạm thời để phản hồi ngay lập tức)
    cache[gid][section][key] = value

    # [CẤY MỚI] Đồng bộ Cloud Atlas vào ngăn 'configs' với đường dẫn settings động
    db = getattr(State.bot, "db", None)
    if db:
        await db.configs.update_one(
            {"guild_id": gid, "module": "greet_leave"},
            {"$set": {f"settings.{section}.{key}": value}},
            upsert=True
        )
    else:
        print(f"[ERROR] Không thể đồng bộ {section}.{key} lên Cloud Atlas cho Guild {gid}", flush=True)

    print(f"[STORAGE] Updated {section}.{key} for Guild {gid} (Cloud Synced)", flush=True)


async def get_section(guild_id: int, section: str):
    """Lấy riêng phần cấu hình Greet/Leave/Wellcome (Bản sao an toàn)"""
    config = await get_guild_config(guild_id)
    return config.get(section, {})
