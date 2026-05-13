import asyncio
import copy

# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
# from core.cache_manager import get_raw, mark_dirty, update

# Khởi tạo một bộ đệm RAM để duy trì vận hành Stateless
_internal_identity_cache = {}

# Chốt chặn bảo mật: Đảm bảo không có xung đột dữ liệu khi ghi đồng thời
_lock = asyncio.Lock()

# =============================
# INTERNAL HELPERS (Nội soi)
# =============================

def _get_cache():
    """Truy xuất kho dữ liệu từ bộ nhớ RAM"""
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Chuyển từ file cục bộ sang bộ đệm RAM
    return _internal_identity_cache

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
    Lưu trữ danh tính vào kho RAM. Hỗ trợ cả 3 loại vỏ:
    - ident_type="manual": Dùng cho cả Loại 1 (Tĩnh) và Loại 2 (Biến số).
    - ident_type="target": Dùng cho Loại 3 (Mượn xác qua ID).
    """
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        nid = _nid(name)

        if gid not in cache:
            cache[gid] = {}

        # Cấu trúc dữ liệu tối ưu Max Ping (Giữ nguyên DNA của Nguyệt)
        identity_data = {
            "type": ident_type,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "target_id": target_id
        }

        cache[gid][nid] = identity_data
        
        # [TRÍ NHỚ ĐÃ BÓC TÁCH] Vô hiệu hóa ghi đĩa cục bộ
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

async def load_identity_raw(guild_id: int, name: str):
    """Phiên bản lấy dữ liệu thô (Internal use)"""
    cache = _get_cache()
    gid = _gid(guild_id)
    nid = _nid(name)
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    return guild_data.get(nid) if guild_data else None

async def delete_identity(guild_id: int, name: str):
    """Xóa một danh tính khỏi kho RAM"""
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        nid = _nid(name)

        if gid in cache and nid in cache[gid]:
            del cache[gid][nid]
            # [TRÍ NHỚ ĐÃ BÓC TÁCH] Vô hiệu hóa ghi đĩa cục bộ
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
