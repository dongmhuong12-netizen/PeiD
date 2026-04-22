import asyncio
from core.cache_manager import load, mark_dirty, get_raw

FILE_KEY = "state"

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
    # Lấy bản gốc trong RAM
    cache = get_raw(FILE_KEY)

    # Khởi tạo cấu trúc nếu chưa có (Sửa trực tiếp vào RAM)
    cache.setdefault("embeds", {})
    cache.setdefault("reactions", {})
    cache.setdefault("ui", {})
    cache.setdefault("runtime", {})

    rt = cache["runtime"]
    rt.setdefault("reaction_cache", {})
    rt.setdefault("message_cache", {})
    rt.setdefault("embed_name_to_message", {})

    return cache


def _write(mutator):
    """
    Thực hiện ghi dữ liệu an toàn vào bộ nhớ cache.
    """
    # Lấy reference trực tiếp
    cache = _get()
    
    # Mutator sẽ thay đổi trực tiếp trên reference này
    mutator(cache)
    
    # Đánh dấu dirty để CacheManager tự flush sau 5s
    mark_dirty(FILE_KEY)


# =========================
# EMBED STATE
# =========================

class State:

    @staticmethod
    async def set_embed(gid: int, name: str, data: dict):
        async with _lock:
            def op(cache):
                gid_s = str(gid)
                # Đảm bảo lưu đúng vào nhánh embeds
                if "embeds" not in cache:
                    cache["embeds"] = {}
                
                cache["embeds"].setdefault(gid_s, {})
                cache["embeds"][gid_s][name] = data

            _write(op)

    @staticmethod
    async def get_embed(gid: int, name: str):
        # Đọc trực tiếp từ RAM để đảm bảo tính thời gian thực
        cache = _get()
        return cache.get("embeds", {}).get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:
            def op(cache):
                gid_s = str(gid)
                if gid_s in cache.get("embeds", {}):
                    cache["embeds"][gid_s].pop(name, None)

                    # Dọn dẹp guild rỗng để tiết kiệm RAM/Disk
                    if not cache["embeds"][gid_s]:
                        cache["embeds"].pop(gid_s, None)

            _write(op)


    # =========================
    # ATOMIC REGISTER
    # =========================

    @staticmethod
    async def atomic_embed_register(gid: int, name: str, message_id: int, reaction_data: dict | None = None):
        async with _tx_lock:
            def op(cache):
                gid_s = str(gid)
                mid_s = str(message_id)

                # NAME -> MESSAGE
                cache["runtime"]["embed_name_to_message"].setdefault(gid_s, {})
                cache["runtime"]["embed_name_to_message"][gid_s][name] = mid_s

                # MESSAGE CACHE (Dùng để truy xuất ngược từ tin nhắn ra tên embed)
                cache["runtime"]["message_cache"][mid_s] = {
                    "guild_id": gid_s,
                    "name": name
                }

                # Đồng bộ Reaction nếu có
                if reaction_data:
                    cache["reactions"][mid_s] = reaction_data
                    cache["runtime"]["reaction_cache"][mid_s] = reaction_data

            _write(op)

    @staticmethod
    async def get_embed_message(gid: int, name: str):
        cache = _get()
        return cache["runtime"]["embed_name_to_message"].get(str(gid), {}).get(name)


    # =========================
    # REACTIONS
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

        # Ưu tiên lấy từ runtime cache (RAM) trước
        return (
            cache["runtime"]["reaction_cache"].get(mid_s)
            or cache.get("reactions", {}).get(mid_s)
        )


    # =========================
    # UI
    # =========================

    @staticmethod
    async def set_ui(key: str, data: dict):
        async with _lock:
            def op(cache):
                cache.setdefault("ui", {})
                cache["ui"][key] = data

            _write(op)

    @staticmethod
    async def get_ui(key: str):
        cache = _get()
        return cache.get("ui", {}).get(key)


    # =========================
    # RUNTIME RESET
    # =========================

    @staticmethod
    async def clear_rt():
        """Reset các dữ liệu tạm thời khi bot khởi động hoặc lỗi"""
        async with _lock:
            def op(cache):
                cache["runtime"] = {
                    "reaction_cache": {},
                    "message_cache": {},
                    "embed_name_to_message": {}
                }

            _write(op)


    # =========================
    # RESYNC
    # =========================

    @staticmethod
    async def force_resync():
        """Ép bot nạp lại file từ đĩa vào RAM"""
        load(FILE_KEY)
        return True
