import asyncio
import discord
import time # [THÊM] để check thời gian hết hạn test
from core.cache_manager import load, mark_dirty, get_raw

FILE_KEY = "state"

# Sử dụng lock cho các thao tác quan trọng để tránh race condition ở RAM
_lock = asyncio.Lock()
_tx_lock = asyncio.Lock()

# =========================
# SAFE READ/WRITE LAYER
# =========================

def _get():
    """
    Lấy reference trực tiếp từ RAM của CacheManager.
    Đảm bảo mọi thay đổi được phản ánh ngay lập tức.
    """
    cache = get_raw(FILE_KEY)

    # Khởi tạo cấu trúc dữ liệu bền vững (Tiêu chuẩn 100k+)
    cache.setdefault("embeds", {})
    cache.setdefault("reactions", {})
    cache.setdefault("ui", {})
    
    # Sổ hộ khẩu: NAME <-> MESSAGE (Chống mất trí nhớ sau Restart)
    cache.setdefault("mapping", {
        "name_to_mid": {}, # {gid: {name: mid}}
        "mid_to_info": {}  # {mid: {gid: gid, name: name}}
    })

    # Nhánh runtime: Chỉ chứa dữ liệu tạm thời, không lưu xuống đĩa
    cache.setdefault("runtime", {
        "reaction_cache": {} 
    })

    return cache

def _write(mutator):
    """
    Thực hiện ghi dữ liệu an toàn vào bộ nhớ cache.
    """
    cache = _get()
    mutator(cache)
    
    # Đánh dấu dữ liệu đã thay đổi để CacheManager tự động lưu sau 5s
    mark_dirty(FILE_KEY)

# =========================
# EMBED STATE (TRÍ NHỚ)
# =========================

class State:

    @staticmethod
    async def set_embed(gid: int, name: str, data: dict):
        async with _lock:
            def op(cache):
                gid_s = str(gid)
                cache["embeds"].setdefault(gid_s, {})
                cache["embeds"][gid_s][name] = data
            _write(op)

    @staticmethod
    async def get_embed(gid: int, name: str):
        cache = _get()
        return cache.get("embeds", {}).get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:
            def op(cache):
                gid_s = str(gid)
                # 1. Xóa Embed gốc
                if gid_s in cache["embeds"]:
                    cache["embeds"][gid_s].pop(name, None)
                    if not cache["embeds"][gid_s]:
                        cache["embeds"].pop(gid_s, None)
                
                # [VÁ LỖI LEAK] 2. Garbage Collection: Dọn sạch rác mồ côi trong mapping và reaction
                if "mapping" in cache:
                    mid_s = cache["mapping"]["name_to_mid"].get(gid_s, {}).pop(name, None)
                    if mid_s:
                        if not cache["mapping"]["name_to_mid"].get(gid_s):
                            cache["mapping"]["name_to_mid"].pop(gid_s, None)
                        
                        cache["mapping"]["mid_to_info"].pop(mid_s, None)
                        cache.get("reactions", {}).pop(mid_s, None)
                        cache.get("runtime", {}).get("reaction_cache", {}).pop(mid_s, None)
            _write(op)

    # =========================
    # ATOMIC REGISTER (LIÊN KẾT BỀN VỮNG)
    # =========================

    @staticmethod
    async def atomic_embed_register(gid: int, name: str, message_id: int, reaction_data: dict | None = None):
        async with _tx_lock:
            def op(cache):
                gid_s = str(gid)
                mid_s = str(message_id)

                cache["mapping"]["name_to_mid"].setdefault(gid_s, {})
                cache["mapping"]["name_to_mid"][gid_s][name] = mid_s

                cache["mapping"]["mid_to_info"][mid_s] = {
                    "guild_id": gid_s,
                    "name": name
                }

                if reaction_data:
                    cache["reactions"][mid_s] = reaction_data
                    cache["runtime"]["reaction_cache"][mid_s] = reaction_data

            _write(op)
            print(f"[STATE] Đã đăng ký liên kết bền vững: {name} -> {message_id}", flush=True)

    @staticmethod
    async def get_embed_message(gid: int, name: str):
        cache = _get()
        return cache["mapping"]["name_to_mid"].get(str(gid), {}).get(name)

    @staticmethod
    async def get_info_by_mid(mid: int):
        cache = _get()
        return cache["mapping"]["mid_to_info"].get(str(mid))

    # =========================
    # REACTIONS & UI
    # =========================

    @staticmethod
    async def set_reaction(mid: int, data: dict):
        async with _lock:
            def op(cache):
                mid_s = str(mid)
                cache["reactions"][mid_s] = data
                cache["runtime"]["reaction_cache"][mid_s] = data
            _write(op)

    @staticmethod
    async def get_reaction(mid: int):
        cache = _get()
        mid_s = str(mid)
        return cache["runtime"]["reaction_cache"].get(mid_s) or cache["reactions"].get(mid_s)

    @staticmethod
    async def set_ui(key: str, data: dict):
        async with _lock:
            def op(cache):
                cache["ui"][key] = data
            _write(op)

    @staticmethod
    async def get_ui(key: str):
        """
        Lấy dữ liệu UI và tự động dọn dẹp dữ liệu quá hạn.
        """
        cache = _get()
        data = cache["ui"].get(key)
        
        # [FIX] Tự động xóa rác nếu phát hiện đã hết hạn test
        if data and isinstance(data, dict) and "expiry" in data:
            if time.time() > data["expiry"]:
                async with _lock:
                    def op(cache):
                        cache["ui"].pop(key, None)
                    _write(op)
                return None
        return data

    @staticmethod
    async def del_ui(key: str):
        """Xóa UI state thủ công"""
        async with _lock:
            def op(cache):
                cache["ui"].pop(key, None)
            _write(op)

    # =========================
    # SYSTEM OPS
    # =========================

    @staticmethod
    async def clear_rt():
        async with _lock:
            def op(cache):
                cache["runtime"] = {"reaction_cache": {}}
            _write(op)
            print("[STATE] Đã dọn dẹp bộ nhớ đệm Runtime.", flush=True)

    @staticmethod
    async def resync():
        try:
            load(FILE_KEY)
            _get() 
            print(f"[STATE] Trí nhớ '{FILE_KEY}' đã được khôi phục thành công.", flush=True)
            return True
        except Exception as e:
            print(f"[STATE ERROR] Không thể khôi phục trí nhớ: {e}", flush=True)
            return False
