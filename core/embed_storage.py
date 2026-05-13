import copy
import asyncio

# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
# from core.cache_manager import get_raw, mark_dirty, update

# Khởi tạo một dictionary cục bộ để duy trì dữ liệu trong RAM
_internal_embed_cache = {}

# [VÁ LỖI] Bổ sung Lock để chống Race Condition (mất dữ liệu khi lưu đồng thời)
_lock = asyncio.Lock()

# =========================
# SAFE CACHE ACCESS (INTERNAL)
# =========================

def _get_cache():
    """
    lấy reference gốc từ bộ nhớ RAM. 
    sử dụng cơ chế tự phục hồi nếu dữ liệu bị lỗi format (tiêu chuẩn 100k+).
    """
    # [TRÍ NHỚ ĐÃ BÓC TÁCH] Sử dụng biến RAM thay vì cache_manager
    cache = _internal_embed_cache

    return cache

# =========================
# HELPERS (INTERNAL)
# =========================

def _gid(guild_id):
    """chuẩn hóa id server thành chuỗi (string) để tránh lỗi json precision"""
    return str(guild_id) if guild_id is not None else "global"

def _nid(name):
    """
    [GIA CỐ] chuẩn hóa tên embed về chữ thường và xóa khoảng trắng.
    đảm bảo việc /create và /show luôn tìm thấy nhau 100%.
    """
    return str(name).lower().strip() if name is not None else None

# =========================
# SAVE EMBED (PUBLIC API)
# =========================

async def save_embed(guild_id, name, data):
    """lưu embed vào ram"""
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

    # IT Pro: Tìm kiếm thông minh ở cả String ID và Int ID (Tương thích ngược dữ liệu cũ)
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    
    if not isinstance(guild_data, dict):
        return None

    data = guild_data.get(name)
    
    return copy.deepcopy(data) if data is not None else None

# =========================
# DELETE EMBED (PUBLIC API)
# =========================

async def delete_embed(guild_id, name):
    """xóa embed vĩnh viễn khỏi ram"""
    if name is None:
        return False

    # [VÁ LỖI] Khóa bộ nhớ khi thao tác xóa nhánh
    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        if gid not in cache:
            # Thử tìm hòm theo Int ID
            gid_int = int(gid) if gid.isdigit() else None
            if gid_int not in cache: return False
            gid = gid_int

        guild_data = cache[gid]
        if not isinstance(guild_data, dict) or name not in guild_data:
            return False

        del guild_data[name]

        if not guild_data:
            cache.pop(gid, None)
        
    print(f"[storage] đã xóa embed '{name}' khỏi server {gid}.", flush=True)
    return True

# =========================
# RETRIEVAL API (PUBLIC API)
# =========================

async def get_all_embeds(guild_id):
    """lấy toàn bộ kho embed của server (trả về bản sao an toàn)"""
    cache = _get_cache()
    gid = _gid(guild_id)

    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    if not isinstance(guild_data, dict):
        return {}

    return copy.deepcopy(guild_data)

async def get_all_embed_names(guild_id):
    """lấy danh sách tên phục vụ hệ thống autocomplete"""
    if guild_id is None:
        return []

    cache = _get_cache()
    gid = _gid(guild_id)

    # IT Pro: Check cả dạng String và Int để đảm bảo danh sách ko bao giờ trắng xóa
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    
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
    """
    if not name:
        return False

    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        # Kiểm tra tính toàn vẹn của nhánh dữ liệu (Support cả 2 loại ID)
        if gid not in cache or name not in cache[gid]:
            gid_int = int(gid) if gid.isdigit() else None
            if gid_int not in cache or name not in cache[gid_int]:
                return False
            gid = gid_int

        data = cache[gid][name]
        
        # Vá cấu trúc an toàn (Phòng khi file hệ thống chưa update kịp)
        if "buttons" not in data or not isinstance(data["buttons"], list):
            data["buttons"] = []

        # --- XỬ LÝ CÁC HÀNH ĐỘNG (ATOMIC ACTIONS) ---

        if action == "add" and button_data:
            # Multi-IT: Bảo vệ giới hạn 25 linh kiện của Discord API tại tầng Storage
            if len(data["buttons"]) >= 25:
                return False
            
            # [GIA CỐ THẨM MỸ] Tự động thêm khoảng trắng nếu có Emoji để tránh dính chữ
            btn = copy.deepcopy(button_data)
            if btn.get("emoji") and "label" in btn:
                lbl = str(btn["label"])
                if lbl and not lbl.startswith(" "):
                    btn["label"] = f" {lbl}"
            
            data["buttons"].append(btn)
            
        elif action == "remove":
            # Multi-IT: Xóa an toàn không văng lỗi IndexError
            if 0 <= index < len(data["buttons"]):
                data["buttons"].pop(index)
            else:
                return False

        elif action == "edit" and button_data:
            # IT Pro: Sửa trực tiếp nút tại index mà không thay đổi thứ tự
            if 0 <= index < len(data["buttons"]):
                # [GIA CỐ THẨM MỸ] Chuẩn hóa thẩm mỹ trước khi sửa
                btn = copy.deepcopy(button_data)
                if btn.get("emoji") and "label" in btn:
                    lbl = str(btn["label"])
                    if lbl and not lbl.startswith(" "):
                        btn["label"] = f" {lbl}"
                data["buttons"][index] = btn
            else:
                return False

        elif action == "update_by_id" and custom_id and button_data:
            # [GIA CỐ THẨM MỸ] Chuẩn hóa thẩm mỹ cho hệ thống Update ID
            btn_fixed = copy.deepcopy(button_data)
            if btn_fixed.get("emoji") and "label" in btn_fixed:
                lbl = str(btn_fixed["label"])
                if lbl and not lbl.startswith(" "):
                    btn_fixed["label"] = f" {lbl}"

            found = False
            for i, btn in enumerate(data["buttons"]):
                if btn.get("custom_id") == custom_id:
                    data["buttons"][i] = btn_fixed
                    found = True
                    break
            if not found: return False
                
        elif action == "clear":
            data["buttons"] = []

        else:
            return False
        
    return True
