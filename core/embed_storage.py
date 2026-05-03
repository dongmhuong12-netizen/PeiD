from core.cache_manager import get_raw, mark_dirty, update
import copy
import asyncio

FILE_KEY = "embeds"

# [VÁ LỖI] Bổ sung Lock để chống Race Condition (mất dữ liệu khi lưu đồng thời)
_lock = asyncio.Lock()

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
        # [VÁ LỖI] Ép khởi tạo vùng nhớ mới và đồng bộ ngược về cache_manager
        cache = {}
        update(FILE_KEY, cache)
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

    # [VÁ LỖI] Khóa bộ nhớ tạm để thao tác khởi tạo key không bị đè nhau
    async with _lock:
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

    # [VÁ LỖI] Khóa bộ nhớ khi thao tác xóa nhánh
    async with _lock:
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

# =========================
# BUTTONS API (PHASE 3 - ATOMIC UPDATES)
# =========================

async def atomic_update_button(guild_id, name, button_data: dict = None, action: str = "add", index: int = -1, custom_id: str = None):
    """
    [MULTI-IT] Thao tác an toàn tuyệt đối với mảng nút bấm.
    Ngăn chặn Race Condition (xóa đè dữ liệu) khi nhiều thao tác diễn ra cùng 1 miligiây.
    Hỗ trợ: 
    - 'add': Thêm nút mới.
    - 'remove': Xóa theo vị trí index.
    - 'clear': Xóa sạch nút.
    - 'edit': Sửa dữ liệu nút tại vị trí index cụ thể.
    - 'update_by_id': Tìm nút theo custom_id và cập nhật dữ liệu (Dùng cho Gacha/Vote).
    """
    if not name:
        return False

    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        # Kiểm tra tính toàn vẹn của nhánh dữ liệu
        if gid not in cache or not isinstance(cache[gid], dict):
            return False
            
        if name not in cache[gid]:
            return False

        data = cache[gid][name]
        
        # Vá cấu trúc an toàn (Phòng khi file hệ thống chưa update kịp)
        if "buttons" not in data or not isinstance(data["buttons"], list):
            data["buttons"] = []

        # --- XỬ LÝ CÁC HÀNH ĐỘNG (ATOMIC ACTIONS) ---

        if action == "add" and button_data:
            # Multi-IT: Bảo vệ giới hạn 25 linh kiện của Discord API tại tầng Storage
            if len(data["buttons"]) >= 25:
                return False
            data["buttons"].append(copy.deepcopy(button_data))
            
        elif action == "remove":
            # Multi-IT: Xóa an toàn không văng lỗi IndexError
            if 0 <= index < len(data["buttons"]):
                data["buttons"].pop(index)
            else:
                return False

        elif action == "edit" and button_data:
            # IT Pro: Sửa trực tiếp nút tại index mà không thay đổi thứ tự
            if 0 <= index < len(data["buttons"]):
                data["buttons"][index] = copy.deepcopy(button_data)
            else:
                return False

        elif action == "update_by_id" and custom_id and button_data:
            # IT Pro: Tìm và cập nhật nút dựa trên ID (Quan trọng cho hệ thống Reaction/Interaction)
            found = False
            for i, btn in enumerate(data["buttons"]):
                if btn.get("custom_id") == custom_id:
                    data["buttons"][i] = copy.deepcopy(button_data)
                    found = True
                    break
            if not found: return False
                
        elif action == "clear":
            data["buttons"] = []

        else:
            # Hành động không hợp lệ
            return False

        # Đánh dấu dữ liệu đã thay đổi để CacheManager làm việc
        mark_dirty(FILE_KEY)
        
    return True


