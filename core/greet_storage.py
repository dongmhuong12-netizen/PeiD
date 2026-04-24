import json
import os
from core.cache_manager import get_raw, mark_dirty

# Sử dụng chung key với CacheManager để đồng bộ hóa
FILE_KEY = "greet_leave"

# =========================
# INTERNAL HELPERS
# =========================

def _get_cache():
    """Lấy dữ liệu trực tiếp từ RAM của CacheManager"""
    return get_raw(FILE_KEY)

# =========================
# PUBLIC API
# =========================

def get_guild_config(guild_id: int):
    """Lấy toàn bộ cấu hình của một Guild từ RAM"""
    cache = _get_cache()
    return cache.get(str(guild_id), {})


def update_guild_config(guild_id: int, section: str, key: str, value):
    """
    Cập nhật cấu hình vào RAM và đánh dấu ghi xuống Disk sau 5 giây.
    section: "greet" hoặc "leave"
    key: "channel" | "embed" | "message"
    """
    cache = _get_cache()
    gid = str(guild_id)

    # Đảm bảo cấu trúc Guild tồn tại trong RAM
    if gid not in cache:
        cache[gid] = {
            "greet": {},
            "leave": {}
        }
    
    if not isinstance(cache[gid], dict):
        cache[gid] = {"greet": {}, "leave": {}}

    if section not in cache[gid]:
        cache[gid][section] = {}

    # Cập nhật giá trị trực tiếp trên reference của RAM
    cache[gid][section][key] = value

    # Đánh dấu "Dirty" để CacheManager tự động lưu xuống Disk ngầm
    mark_dirty(FILE_KEY)


def get_section(guild_id: int, section: str):
    """Lấy một phần cấu hình (greet hoặc leave) của Guild"""
    config = get_guild_config(guild_id)
    return config.get(section, {})
