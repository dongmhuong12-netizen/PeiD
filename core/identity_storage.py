import asyncio
import copy
from core.cache_manager import get_raw, mark_dirty, update

# Định danh file lưu trữ trong hệ thống Cache
FILE_KEY = "identities"

# Chốt chặn bảo mật: Đảm bảo không có xung đột dữ liệu khi ghi đồng thời
_lock = asyncio.Lock()

# =============================
# INTERNAL HELPERS (Nội soi)
# =============================

def _get_cache():
    """Truy xuất kho dữ liệu thô từ Cache Manager"""
    cache = get_raw(FILE_KEY)
    if not isinstance(cache, dict):
        cache = {}
        update(FILE_KEY, cache)
        mark_dirty(FILE_KEY)
    return cache

def _gid(guild_id):
    """Chuẩn hóa ID Server sang chuỗi (String)"""
    return str(guild_id)

def _nid(name):
    """Chuẩn hóa tên định danh (ID Name): Viết thường, không dấu cách thừa"""
    return str(name).lower().strip()

# =============================
# PUBLIC API (Giao diện lập trình)
# =============================

async def save_identity(guild_id: int, name: str, display_name: str = None, avatar_url: str = None, target_id: str = None, ident_type: str = "manual"):
    """
    Lưu trữ danh tính vào kho. Hỗ trợ cả 3 loại vỏ:
    - ident_type="manual": Dùng cho cả Loại 1 (Tĩnh) và Loại 2 (Biến số).
    - ident_type="target": Dùng cho Loại 3 (Mượn xác qua ID).
    """
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        nid = _nid(name)

        if gid not in cache:
            cache[gid] = {}

        # Cấu trúc dữ liệu tối ưu Max Ping
        identity_data = {
            "type": ident_type,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "target_id": target_id
        }

        cache[gid][nid] = identity_data
        
        # Đẩy dữ liệu vào cache và đánh dấu cần lưu vào ổ đĩa
        update(FILE_KEY, cache)
        mark_dirty(FILE_KEY)
        return True

async def load_identity(guild_id: int, name: str):
    """Tải dữ liệu danh tính dựa trên ID Server và tên gợi nhớ"""
    cache = _get_cache()
    gid = _gid(guild_id)
    nid = _nid(name)

    # Hỗ trợ tìm kiếm linh hoạt (String/Int)
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if not guild_data:
        return None

    data = guild_data.get(nid)
    # Deepcopy để tránh việc sửa đổi dữ liệu gốc trong Cache khi đang xử lý
    return copy.deepcopy(data) if data else None

async def delete_identity(guild_id: int, name: str):
    """Xóa vĩnh viễn một danh tính khỏi kho lưu trữ"""
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        nid = _nid(name)

        if gid in cache and nid in cache[gid]:
            del cache[gid][nid]
            update(FILE_KEY, cache)
            mark_dirty(FILE_KEY)
            return True
        return False

async def get_all_identity_names(guild_id: int):
    """Lấy danh sách tất cả tên 'vỏ' để phục vụ Autocomplete"""
    cache = _get_cache()
    gid = _gid(guild_id)
    
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if not guild_data:
        return []
        
    return list(guild_data.keys())
