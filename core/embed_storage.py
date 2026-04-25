from core.cache_manager import get_raw, mark_dirty
import copy

FILE_KEY = "embeds"

# =========================
# SAFE CACHE ACCESS
# =========================

def _get_cache():
    """
    Lấy reference gốc từ CacheManager. 
    Sử dụng cơ chế tự phục hồi nếu dữ liệu bị lỗi format (Tiêu chuẩn 100k+).
    """
    cache = get_raw(FILE_KEY)

    # Đảm bảo cache luôn là dict. Nếu lỡ là list hoặc None (do file hỏng), reset về dict.
    if not isinstance(cache, dict):
        print(f"[STORAGE WARNING] Cache '{FILE_KEY}' bị sai định dạng. Đang khởi động lại...", flush=True)
        # Xóa mọi thứ bên trong và đưa về dict (vì cache là reference đến RAM của CacheManager)
        if hasattr(cache, "clear"):
            cache.clear()
        # Lưu ý: Không gán lại cache = {} vì sẽ làm mất reference gốc. 
        # CacheManager đã đảm bảo get_raw trả về một object có thể mutate.
        mark_dirty(FILE_KEY)

    return cache

# =========================
# HELPERS
# =========================

def _gid(guild_id):
    """Chuẩn hóa ID Server thành chuỗi (String) để tránh lỗi JSON Precision"""
    return str(guild_id) if guild_id is not None else "global"

def _nid(name):
    """Chuẩn hóa tên Embed"""
    return str(name) if name is not None else None

# =========================
# SAVE EMBED
# =========================

def save_embed(guild_id, name, data):
    """Lưu Embed vào RAM và kích hoạt hàng đợi ghi đĩa"""
    if not name or data is None:
        return False

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    # Khởi tạo Guild-space nếu chưa có
    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {}

    # ATOMIC COPY: Dùng deepcopy để các file logic không vô tình sửa hỏng RAM gốc
    cache[gid][name] = copy.deepcopy(data)

    # Đánh dấu dữ liệu bẩn để CacheManager tự ghi xuống Disk sau 5 giây
    mark_dirty(FILE_KEY)
    
    print(f"[STORAGE] Đã lưu Embed '{name}' cho Server {gid} vào bộ nhớ tạm.", flush=True)
    return True

# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name):
    """Tải Embed từ RAM với tốc độ cao"""
    if name is None:
        return None

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return None

    data = guild_data.get(name)
    
    # LUÔN TRẢ VỀ DEEPCOPY: Đảm bảo tính nguyên tử (Atomic)
    # File nhận dữ liệu có quyền sửa thoải mái mà không ảnh hưởng đến "ký ức" của Bot
    return copy.deepcopy(data) if data is not None else None

# =========================
# DELETE EMBED
# =========================

def delete_embed(guild_id, name):
    """Xóa Embed vĩnh viễn khỏi RAM và Disk"""
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

    # Xóa khỏi RAM
    del guild_data[name]

    # Nếu guild không còn embed nào, dọn dẹp để tiết kiệm tài nguyên
    if not guild_data:
        cache.pop(gid, None)

    mark_dirty(FILE_KEY)
    print(f"[STORAGE] Đã xóa Embed '{name}' khỏi Server {gid}.", flush=True)
    return True

# =========================
# RETRIEVAL API
# =========================

def get_all_embeds(guild_id):
    """Lấy toàn bộ kho Embed của server (Trả về bản sao an toàn)"""
    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return {}

    return copy.deepcopy(guild_data)

def get_all_embed_names(guild_id):
    """Lấy danh sách tên phục vụ hệ thống Autocomplete"""
    if guild_id is None:
        return []

    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
