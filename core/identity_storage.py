import asyncio
import copy
# [CẤY MỚI] Kết nối với não bộ bot.db thông qua State
from core.state import State

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
    Lưu trữ danh tính vào kho RAM + Đồng bộ Cloud Atlas. Hỗ trợ cả 3 loại vỏ:
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
        
        # [CẤY MỚI] Đồng bộ dữ liệu lên ngăn 'identities' của Cloud
        db = getattr(State.bot, "db", None)
        if db:
            await db.identities.update_one(
                {"guild_id": gid, "name": nid},
                {"$set": {"data": identity_data}},
                upsert=True
            )
            
        print(f"[STORAGE] Identity '{nid}' saved for Guild {gid} (Cloud Synced)", flush=True)
        return True

async def load_identity(guild_id: int, name: str):
    """Tải dữ liệu danh tính từ RAM (Max Ping) hoặc Cloud Atlas (Self-healing)"""
    cache = _get_cache()
    gid = _gid(guild_id)
    nid = _nid(name)

    # 1. Ưu tiên tìm trong RAM
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if isinstance(guild_data, dict) and nid in guild_data:
        return copy.deepcopy(guild_data[nid])

    # 2. [CẤY MỚI] Nếu RAM hụt (do Reboot), truy vấn Cloud Atlas
    db = getattr(State.bot, "db", None)
    if db:
        doc = await db.identities.find_one({"guild_id": gid, "name": nid})
        if doc:
            if gid not in cache: cache[gid] = {}
            cache[gid][nid] = doc["data"]
            return copy.deepcopy(doc["data"])

    return None

async def load_identity_raw(guild_id: int, name: str):
    """Phiên bản lấy dữ liệu thô (Internal use) - Tích hợp Cloud khôi phục"""
    cache = _get_cache()
    gid = _gid(guild_id)
    nid = _nid(name)
    
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if isinstance(guild_data, dict) and nid in guild_data:
        return guild_data.get(nid)

    # [CẤY MỚI] Khôi phục dữ liệu thô từ Cloud
    db = getattr(State.bot, "db", None)
    if db:
        doc = await db.identities.find_one({"guild_id": gid, "name": nid})
        if doc:
            if gid not in cache: cache[gid] = {}
            cache[gid][nid] = doc["data"]
            return doc["data"]

    return None

async def delete_identity(guild_id: int, name: str):
    """Xóa một danh tính khỏi RAM & Cloud Atlas"""
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        nid = _nid(name)

        if gid in cache and nid in cache[gid]:
            del cache[gid][nid]
            
            # [CẤY MỚI] Xóa vĩnh viễn trên Cloud Atlas
            db = getattr(State.bot, "db", None)
            if db:
                await db.identities.delete_one({"guild_id": gid, "name": nid})
                
            return True
        return False

async def get_all_identities(guild_id: int):
    """
    Lấy toàn bộ danh sách danh tính của server.
    [GIA CỐ] Tự động khôi phục toàn bộ từ Cloud nếu RAM trống sau reboot.
    """
    cache = _get_cache()
    gid = _gid(guild_id)

    # Nếu RAM trống, thực hiện nạp hàng loạt từ Cloud Atlas (Industrial Logic)
    db = getattr(State.bot, "db", None)
    if gid not in cache and db:
        cursor = db.identities.find({"guild_id": gid})
        async for doc in cursor:
            if gid not in cache: cache[gid] = {}
            cache[gid][doc["name"]] = doc["data"]

    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if not isinstance(guild_data, dict):
        return {}

    return copy.deepcopy(guild_data)

async def get_all_identity_names(guild_id: int):
    """Lấy danh sách tất cả tên 'vỏ' để phục vụ Autocomplete"""
    if guild_id is None:
        return []

    # Gọi get_all_identities để đảm bảo RAM đã được nạp từ Cloud trước khi liệt kê
    guild_data = await get_all_identities(guild_id)
    
    if not isinstance(guild_data, dict):
        return []
        
    return list(guild_data.keys())
