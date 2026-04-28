import copy
from core.cache_manager import get_raw, mark_dirty, update

# Sử dụng chung key để CacheManager tự động quản lý Disk I/O
FILE_KEY = "greet_leave"

# =========================
# INTERNAL HELPERS
# =========================

def _get_cache():
    """
    Lấy dữ liệu trực tiếp từ RAM. 
    Tự động sửa lỗi nếu cấu hình file bị hỏng (Self-healing).
    """
    cache = get_raw(FILE_KEY)

    if not isinstance(cache, dict):
        print(f"[STORAGE WARNING] Cache '{FILE_KEY}' không hợp lệ. Đang reset...", flush=True)
        # [VÁ LỖI] Ép khởi tạo lại dict sạch và đồng bộ với CacheManager
        cache = {}
        update(FILE_KEY, cache)
        mark_dirty(FILE_KEY)

    return cache

# =========================
# PUBLIC API
# =========================

def get_guild_config(guild_id: int):
    """
    Lấy toàn bộ cấu hình Greet/Leave của server.
    Trả về Deepcopy để bảo vệ dữ liệu gốc trong RAM.
    """
    cache = _get_cache()
    config = cache.get(str(guild_id), {})
    
    # Bảo vệ RAM gốc khỏi việc bị chỉnh sửa ngoài ý muốn ở tầng Logic
    return copy.deepcopy(config) if config else {"greet": {}, "leave": {}}


def update_guild_config(guild_id: int, section: str, key: str, value):
    """
    Cập nhật cấu hình và kích hoạt hàng đợi ghi đĩa sau 5 giây.
    section: "greet" | "leave"
    key: "channel" | "embed" | "message"
    """
    cache = _get_cache()
    gid = str(guild_id)

    # Khởi tạo không gian lưu trữ cho Guild nếu chưa có
    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {"greet": {}, "leave": {}}

    if section not in cache[gid] or not isinstance(cache[gid][section], dict):
        cache[gid][section] = {}

    # Ghi trực tiếp vào reference trong RAM (Source of Truth)
    cache[gid][section][key] = value

    # Đánh dấu dữ liệu đã thay đổi để CacheManager xử lý ghi đĩa ngầm
    mark_dirty(FILE_KEY)
    print(f"[STORAGE] Updated {section}.{key} for Guild {gid}", flush=True)


def get_section(guild_id: int, section: str):
    """Lấy riêng phần cấu hình Greet hoặc Leave (Bản sao an toàn)"""
    config = get_guild_config(guild_id)
    return config.get(section, {})
