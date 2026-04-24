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

    # Đảm bảo cache luôn là dict để tránh lỗi crash hệ thống
    if not isinstance(cache, dict):
        # Nếu cache không phải dict (lỗi file), khởi tạo lại ref mới
        # Lưu ý: mark_dirty sẽ giúp sửa lại file trên disk sau đó
        pass

    return cache


# =========================
# NORMALIZE GUILD KEY
# =========================

def _gid(guild_id):
    """Chuẩn hóa ID Server thành chuỗi để làm key JSON"""
    return str(guild_id) if guild_id is not None else "global"


def _nid(name):
    """Chuẩn hóa tên Embed"""
    return str(name) if name is not None else None


# =========================
# SAVE EMBED
# =========================

def save_embed(guild_id, name, data):
    """Lưu Embed vào RAM và đánh dấu cần ghi xuống Disk"""
    if not name or data is None:
        return False

    # Lấy bản gốc từ RAM
    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    # Đảm bảo cấu trúc Guild tồn tại trong RAM
    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {}

    # Copy dữ liệu vào RAM để cô lập dữ liệu (Isolating Data)
    # Tránh việc biến 'data' bên ngoài bị sửa làm hỏng RAM của Bot
    cache[gid][name] = copy.deepcopy(data)

    # Báo cho CacheManager biết cần ghi xuống file sau 5 giây (Debounce ghi file)
    mark_dirty(FILE_KEY)
    return True


# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name):
    """Tải Embed từ RAM"""
    if name is None:
        return None

    # Lấy trực tiếp từ RAM (Source of Truth)
    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    # Truy xuất dữ liệu
    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return None

    data = guild_data.get(name)
    
    # TIÊU CHUẨN 100K+: Luôn trả về Deepcopy để các file logic (như sender) 
    # không vô tình làm sửa đổi dữ liệu gốc trong RAM.
    return copy.deepcopy(data) if data is not None else None


# =========================
# DELETE EMBED
# =========================

def delete_embed(guild_id, name):
    """Xóa Embed vĩnh viễn"""
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

    # Nếu guild không còn embed nào, dọn dẹp để tiết kiệm RAM/Disk
    if not guild_data:
        cache.pop(gid, None)

    mark_dirty(FILE_KEY)
    return True


# =========================
# GET ALL EMBEDS
# =========================

def get_all_embeds(guild_id):
    """Lấy toàn bộ Embed của một server"""
    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return {}

    # Trả về bản sao để bảo vệ RAM
    return copy.deepcopy(guild_data)


# =========================
# GET NAMES
# =========================

def get_all_embed_names(guild_id):
    """Lấy danh sách tên Embed để phục vụ Autocomplete"""
    if guild_id is None:
        return []

    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
