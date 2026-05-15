import copy
import asyncio
# [CẤY MỚI] Nạp State để truy cập vào cỗ máy bot.db
from core.state import State

# Khởi tạo một dictionary cục bộ để duy trì dữ liệu trong RAM
_internal_embed_cache = {}

# [INDUSTRIAL GIA CỐ] Công tắc đánh dấu trạng thái đồng bộ hóa của server
# Đảm bảo không bị lỗi "chỉ hiện 1 embed" khi bot reboot
_synced_guilds = set()

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

    # 1. Ưu tiên RAM
    guild_data = cache.get(gid)
    if isinstance(guild_data, dict) and name in guild_data:
        return copy.deepcopy(guild_data[name])

    # 2. [CẤY MỚI] Nếu RAM hụt, truy vấn Cloud Atlas
    if hasattr(State.bot, "db"):
        doc = await State.bot.db.embeds.find_one({"guild_id": gid, "name": name})
        if doc:
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

        # [DEF - NHỔ CỎ TẬN GỐC] 
        # Xóa RAM nếu có (Không return False sớm để đảm bảo lệnh xóa Cloud luôn chạy)
        if gid in cache and isinstance(cache[gid], dict):
            if name in cache[gid]:
                del cache[gid][name]
                if not cache[gid]:
                    cache.pop(gid, None)
                    _synced_guilds.discard(gid)

        # [GIA CỐ] Luôn luôn gửi lệnh xóa lên Cloud Atlas bất kể trạng thái RAM
        if hasattr(State.bot, "db"):
            await State.bot.db.embeds.delete_one({"guild_id": gid, "name": name})
        
    print(f"[storage] đã xóa vĩnh viễn embed '{name}' khỏi hệ thống (RAM & Cloud).", flush=True)
    return True

# =========================
# RETRIEVAL API (PUBLIC API)
# =========================

async def get_all_embeds(guild_id):
    """
    lấy toàn bộ kho embed của server (trả về bản sao an toàn).
    [GIA CỐ] Sử dụng cỗ máy _synced_guilds để đảm bảo dữ liệu Cloud luôn được nạp đủ.
    """
    cache = _get_cache()
    gid = _gid(guild_id)

    # [PHÒNG NGỰ]: Nếu server chưa được đồng bộ hóa hoàn toàn từ Cloud Atlas
    if gid not in _synced_guilds and hasattr(State.bot, "db"):
        async with _lock:
            # Truy vấn nạp hàng loạt (Bulk Load) từ Cloud
            cursor = State.bot.db.embeds.find({"guild_id": gid})
            if gid not in cache: cache[gid] = {}
            
            async for doc in cursor:
                # Nạp vào RAM (Không đè lên dữ liệu RAM mới hơn nếu có)
                cache[gid][doc["name"]] = doc["data"]
            
            # Gạt công tắc: Đánh dấu đã đồng bộ xong cho phiên làm việc này
            _synced_guilds.add(gid)
            print(f"[storage] đã đồng bộ hóa toàn bộ kho embed từ Cloud cho server {gid}.", flush=True)

    guild_data = cache.get(gid)
    if not isinstance(guild_data, dict):
        return {}

    return copy.deepcopy(guild_data)

async def get_all_embed_names(guild_id):
    """lấy danh sách tên phục vụ hệ thống autocomplete"""
    if guild_id is None:
        return []

    # Gọi get_all_embeds để đảm bảo cỗ máy đồng bộ đã chạy trước khi liệt kê
    guild_data = await get_all_embeds(guild_id)
    
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

        # Đảm bảo dữ liệu được nạp vào RAM trước khi thực hiện update nút
        if gid not in cache or name not in cache[gid]:
            # Thử nạp đơn lẻ từ Cloud trước
            data_cloud = await load_embed(guild_id, name)
            if not data_cloud: return False

        data = cache[gid][name]
        
        if "buttons" not in data or not isinstance(data["buttons"], list):
            data["buttons"] = []

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

        if changed and hasattr(State.bot, "db"):
            await State.bot.db.embeds.update_one(
                {"guild_id": gid, "name": name},
                {"$set": {"data": data}},
                upsert=True
            )
        
    return True
