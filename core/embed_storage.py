from core.cache_manager import get_raw, mark_dirty
import copy
import asyncio

FILE_KEY = "embeds"

# =========================
# SAFE CACHE ACCESS (INTERNAL)
# =========================

def _get_cache():
    """
    lấy reference gốc từ cachemanager. 
    sử dụng cơ chế tự phục hồi nếu dữ liệu bị lỗi format (tiêu chuẩn 100k+).
    """
    cache = get_raw(FILE_KEY)

    if not isinstance(cache, dict):
        print(f"[storage warning] cache '{FILE_KEY}' bị sai định dạng. đang khởi động lại...", flush=True)
        if hasattr(cache, "clear"):
            cache.clear()
        mark_dirty(FILE_KEY)

    return cache

# =========================
# HELPERS (INTERNAL)
# =========================

def _gid(guild_id):
    """chuẩn hóa id server thành chuỗi (string) để tránh lỗi json precision"""
    return str(guild_id) if guild_id is not None else "global"

def _nid(name):
    """chuẩn hóa tên embed"""
    return str(name) if name is not None else None

# =========================
# SAVE EMBED (PUBLIC API)
# =========================

async def save_embed(guild_id, name, data):
    """lưu embed vào ram và kích hoạt hàng đợi ghi đĩa"""
    if not name or data is None:
        return False

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {}

    cache[gid][name] = copy.deepcopy(data)

    mark_dirty(FILE_KEY)
    
    print(f"[storage] đã lưu embed '{name}' cho server {gid} vào bộ nhớ tạm.", flush=True)
    return True

# =========================
# LOAD EMBED (PUBLIC API)
# =========================

async def load_embed(guild_id, name):
    """tải embed từ ram với tốc độ cao"""
    if name is None:
        return None

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return None

    data = guild_data.get(name)
    
    return copy.deepcopy(data) if data is not None else None

# =========================
# DELETE EMBED (PUBLIC API)
# =========================

async def delete_embed(guild_id, name):
    """xóa embed vĩnh viễn khỏi ram và disk"""
    if name is None:
        return False

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    if gid not in cache:
        return False

    guild_data = cache[gid]
    if not isinstance(guild_data, dict) or name not in guild_data:
        return False

    del guild_data[name]

    if not guild_data:
        cache.pop(gid, None)

    mark_dirty(FILE_KEY)
    print(f"[storage] đã xóa embed '{name}' khỏi server {gid}.", flush=True)
    return True

# =========================
# RETRIEVAL API (PUBLIC API)
# =========================

async def get_all_embeds(guild_id):
    """lấy toàn bộ kho embed của server (trả về bản sao an toàn)"""
    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return {}

    return copy.deepcopy(guild_data)

async def get_all_embed_names(guild_id):
    """lấy danh sách tên phục vụ hệ thống autocomplete"""
    if guild_id is None:
        return []

    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
