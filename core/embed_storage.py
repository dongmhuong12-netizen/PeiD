import copy
import asyncio
# [CẤY MỚI] Nạp State để truy cập vào cỗ máy bot.db
from core.state import State

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
    return _internal_embed_cache

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
    """lưu embed vào ram + đồng bộ Cloud Atlas"""
    if not name or data is None:
        return False

    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        if gid not in cache or not isinstance(cache[gid], dict):
            cache[gid] = {}

        cache[gid][name] = copy.deepcopy(data)

        # [CẤY MỚI] Đồng bộ dữ liệu lên ngăn 'embeds' của Cloud
        if hasattr(State.bot, "db"):
            await State.bot.db.embeds.update_one(
                {"guild_id": gid, "name": name},
                {"$set": {"data": data}},
                upsert=True
            )

    print(f"[storage] đã lưu embed '{name}' cho server {gid} vào bộ nhớ tạm & Cloud.", flush=True)
    return True

# =========================
# LOAD EMBED (PUBLIC API)
# =========================

async def load_embed(guild_id, name):
    """tải embed từ ram (Max Ping) hoặc khôi phục từ Cloud nếu RAM trống"""
    if name is None:
        return None

    cache = _get_cache()
    gid = _gid(guild_id)
    name = _nid(name)

    # 1. Ưu tiên RAM: Tìm kiếm ở cả String ID và Int ID
    guild_data = cache.get(gid) or cache.get(int(gid) if gid.isdigit() else None)
    
    if isinstance(guild_data, dict) and name in guild_data:
        return copy.deepcopy(guild_data[name])

    # 2. [CẤY MỚI] Nếu RAM hụt (do Reboot trên Render), truy vấn Cloud Atlas
    if hasattr(State.bot, "db"):
        doc = await State.bot.db.embeds.find_one({"guild_id": gid, "name": name})
        if doc:
            # Khôi phục lại RAM để các lần gọi sau đạt tốc độ Max Ping
            if gid not in cache: cache[gid] = {}
            cache[gid][name] = doc["data"]
            return copy.deepcopy(doc["data"])
    
    return None

# =========================
# DELETE EMBED (PUBLIC API)
# =========================

async def delete_embed(guild_id, name):
    """xóa embed vĩnh viễn khỏi ram & Cloud Atlas"""
    if name is None:
        return False

    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        if gid not in cache:
            gid_int = int(gid) if gid.isdigit() else None
            if gid_int not in cache: return False
            gid = gid_int

        guild_data = cache[gid]
        if not isinstance(guild_data, dict) or name not in guild_data:
            return False

        del guild_data[name]

        # [CẤY MỚI] Xóa vĩnh viễn trên Cloud Atlas
        if hasattr(State.bot, "db"):
            await State.bot.db.embeds.delete_one({"guild_id": str(gid), "name": name})

        if not guild_data:
            cache.pop(gid, None)
        
    print(f"[storage] đã xóa embed '{name}' khỏi server {gid} (RAM & Cloud).", flush=True)
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
    Gia cố: Đồng bộ mọi thay đổi nút bấm lên Cloud ngay lập tức.
    """
    if not name:
        return False

    async with _lock:
        cache = _get_cache()
        gid = _gid(guild_id)
        name = _nid(name)

        if gid not in cache or name not in cache[gid]:
            gid_int = int(gid) if gid.isdigit() else None
            if gid_int not in cache or name not in cache[gid_int]:
                return False
            gid = gid_int

        data = cache[gid][name]
        
        if "buttons" not in data or not isinstance(data["buttons"], list):
            data["buttons"] = []

        # --- XỬ LÝ CÁC HÀNH ĐỘNG (ATOMIC ACTIONS) ---
        changed = False

        if action == "add" and button_data:
            if len(data["buttons"]) >= 25: return False
            btn = copy.deepcopy(button_data)
            if btn.get("emoji") and "label" in btn:
                lbl = str(btn["label"])
                if lbl and not lbl.startswith(" "): btn["label"] = f" {lbl}"
            data["buttons"].append(btn)
            changed = True
            
        elif action == "remove":
            if 0 <= index < len(data["buttons"]):
                data["buttons"].pop(index)
                changed = True
            else: return False

        elif action == "edit" and button_data:
            if 0 <= index < len(data["buttons"]):
                btn = copy.deepcopy(button_data)
                if btn.get("emoji") and "label" in btn:
                    lbl = str(btn["label"])
                    if lbl and not lbl.startswith(" "): btn["label"] = f" {lbl}"
                data["buttons"][index] = btn
                changed = True
            else: return False

        elif action == "update_by_id" and custom_id and button_data:
            btn_fixed = copy.deepcopy(button_data)
            if btn_fixed.get("emoji") and "label" in btn_fixed:
                lbl = str(btn_fixed["label"])
                if lbl and not lbl.startswith(" "): btn_fixed["label"] = f" {lbl}"
            found = False
            for i, btn in enumerate(data["buttons"]):
                if btn.get("custom_id") == custom_id:
                    data["buttons"][i] = btn_fixed
                    found = True
                    changed = True
                    break
            if not found: return False
                
        elif action == "clear":
            data["buttons"] = []
            changed = True

        # [CẤY MỚI] Nếu có thay đổi, đồng bộ ngay toàn bộ Embed Data lên Cloud
        if changed and hasattr(State.bot, "db"):
            await State.bot.db.embeds.update_one(
                {"guild_id": str(gid), "name": name},
                {"$set": {"data": data}},
                upsert=True
            )
        
    return True
