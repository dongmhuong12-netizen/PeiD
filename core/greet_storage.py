import copy

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
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Sử dụng biến RAM thay vì gọi qua cache_manager
    cache = _internal_greet_cache

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
    Cập nhật cấu hình vào bộ nhớ RAM.
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

    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ lệnh đánh dấu dirty để ghi file cục bộ
    print(f"[STORAGE] Updated {section}.{key} for Guild {gid} (Stateless Mode)", flush=True)


def get_section(guild_id: int, section: str):
    """Lấy riêng phần cấu hình Greet hoặc Leave (Bản sao an toàn)"""
    config = get_guild_config(guild_id)
    return config.get(section, {})
