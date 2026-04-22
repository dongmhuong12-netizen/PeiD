from core.cache_manager import get_raw, mark_dirty
import copy

FILE_KEY = "embeds"


# =========================
# SAFE CACHE ACCESS
# =========================

def _get_cache():
    """
    Lấy reference gốc từ CacheManager. 
    Sửa đổi ở đây sẽ tác động trực tiếp vào RAM.
    """
    cache = get_raw(FILE_KEY)

    # Đảm bảo cache luôn là dict để tránh lỗi crash
    if not isinstance(cache, dict):
        # Lưu ý: Trong thực tế get_raw trả về ref, 
        # nên ta hạn chế gán mới hoàn toàn biến cache
        pass

    return cache


# =========================
# NORMALIZE GUILD KEY
# =========================

def _gid(guild_id):
    """Chuẩn hóa ID Server thành chuỗi"""
    return str(guild_id) if guild_id is not None else "global"


def _nid(name):
    """Chuẩn hóa tên Embed"""
    return str(name) if name is not None else None


# =========================
# SAVE EMBED
# =========================

def save_embed(guild_id, name=None, data=None):
    # Xử lý trường hợp thiếu tham số (Global fallback)
    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    # Lấy bản gốc từ RAM
    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    if not name:
        return False

    # FIX 10/10: Sửa trực tiếp trên reference 'cache'
    if gid not in cache:
        cache[gid] = {}
    
    if not isinstance(cache[gid], dict):
        cache[gid] = {}

    # Copy dữ liệu vào RAM để tránh ảnh hưởng bởi các biến bên ngoài
    cache[gid][name] = copy.deepcopy(data)

    # Báo cho CacheManager biết cần ghi xuống file sau 5 giây
    mark_dirty(FILE_KEY)
    return True


# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name=None):
    if name is None:
        return None

    # Lấy trực tiếp từ RAM (Source of Truth)
    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    # Truy xuất dữ liệu theo Guild và Tên
    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return None

    return guild_data.get(name)


# =========================
# DELETE EMBED
# =========================

def delete_embed(guild_id, name=None):
    if name is None:
        return False

    # Lấy bản gốc từ RAM
    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    if gid not in cache:
        return False

    guild_data = cache[gid]

    if not isinstance(guild_data, dict) or name not in guild_data:
        return False

    # Xóa khỏi RAM
    del guild_data[name]

    # Nếu guild không còn embed nào, dọn dẹp để tiết kiệm bộ nhớ
    if not guild_data:
        cache.pop(gid, None)

    mark_dirty(FILE_KEY)
    return True


# =========================
# GET ALL EMBEDS
# =========================

def get_all_embeds(guild_id):
    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return {}

    # Trả về bản sao để bên ngoài không làm hỏng dữ liệu gốc trong RAM
    return copy.deepcopy(guild_data)


# =========================
# GET NAMES
# =========================

def get_all_embed_names(guild_id=None):
    if guild_id is None:
        return []

    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
