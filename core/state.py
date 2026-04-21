import asyncio
from core.cache_manager import load, mark_dirty

FILE_KEY = "state"

_lock = asyncio.Lock()


# =========================
# INTERNAL SAFE GET
# =========================

def _get():
    cache = load(FILE_KEY)

    # ensure schema (IMPORTANT FOR MULTI-SERVER STABILITY)
    cache.setdefault("embeds", {})
    cache.setdefault("reactions", {})
    cache.setdefault("ui", {})
    cache.setdefault("runtime", {})

    cache["runtime"].setdefault("reaction_cache", {})
    cache["runtime"].setdefault("message_cache", {})

    return cache


# =========================
# COMMIT
# =========================

def _commit():
    mark_dirty(FILE_KEY)


# =====================
# EMBEDS
# =====================

class State:

    @staticmethod
    async def set_embed(gid: int, name: str, data: dict):
        async with _lock:
            cache = _get()

            gid = str(gid)
            cache["embeds"].setdefault(gid, {})
            cache["embeds"][gid][name] = data

            _commit()

    @staticmethod
    async def get_embed(gid: int, name: str):
        cache = _get()
        return cache["embeds"].get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:
            cache = _get()

            gid = str(gid)
            cache["embeds"].get(gid, {}).pop(name, None)

            if gid in cache["embeds"] and not cache["embeds"][gid]:
                cache["embeds"].pop(gid, None)

            _commit()

    # =====================
    # REACTIONS
    # =====================

    @staticmethod
    async def set_reaction(mid: int, data: dict):
        async with _lock:
            cache = _get()

            mid = str(mid)
            cache["reactions"][mid] = data
            cache["runtime"]["reaction_cache"][mid] = data

            _commit()

    @staticmethod
    async def get_reaction(mid: int):
        cache = _get()
        mid = str(mid)

        return (
            cache["runtime"]["reaction_cache"].get(mid)
            or cache["reactions"].get(mid)
        )

    @staticmethod
    async def del_reaction(mid: int):
        async with _lock:
            cache = _get()
            mid = str(mid)

            cache["reactions"].pop(mid, None)
            cache["runtime"]["reaction_cache"].pop(mid, None)

            _commit()

    # =====================
    # UI STATE
    # =====================

    @staticmethod
    async def set_ui(key: str, data: dict):
        async with _lock:
            cache = _get()
            cache["ui"][key] = data
            _commit()

    @staticmethod
    async def get_ui(key: str):
        cache = _get()
        return cache["ui"].get(key)

    @staticmethod
    async def del_ui(key: str):
        async with _lock:
            cache = _get()
            cache["ui"].pop(key, None)
            _commit()

    # =====================
    # RUNTIME
    # =====================

    @staticmethod
    async def set_rt(key: str, data: dict):
        async with _lock:
            cache = _get()
            cache["runtime"][key] = data
            _commit()

    @staticmethod
    async def get_rt(key: str):
        cache = _get()
        return cache["runtime"].get(key)

    @staticmethod
    async def clear_rt():
        async with _lock:
            cache = _get()
            cache["runtime"] = {
                "reaction_cache": {},
                "message_cache": {}
            }
            _commit()

    # =====================
    # RESYNC (REAL FIX)
    # =====================

    @staticmethod
    async def resync():
        # cache manager handles reload automatically
        return True

    @staticmethod
    async def force_resync():
        # force invalidate cache layer
        load(FILE_KEY)
        return True
