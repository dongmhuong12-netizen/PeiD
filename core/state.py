import asyncio
from core.cache_manager import load, mark_dirty, get_raw

FILE_KEY = "state"

_lock = asyncio.Lock()


# =========================
# INTERNAL SAFE GET
# =========================

def _get():
    """
    SAFE READ LAYER
    - always ensure schema
    - avoids mutation on shared reference
    """
    cache = get_raw(FILE_KEY)

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


# =========================
# SAFE WRITE HELPER (C1 CORE FIX)
# =========================

def _write(mutator):
    """
    Atomic mutation wrapper
    ensures:
    - no partial state corruption
    - safe multi-task update
    """
    cache = _get()
    mutator(cache)
    _commit()


# =====================
# EMBEDS
# =====================

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
        return cache["embeds"].get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:

            def op(cache):
                gid_s = str(gid)
                cache["embeds"].get(gid_s, {}).pop(name, None)

                if gid_s in cache["embeds"] and not cache["embeds"][gid_s]:
                    cache["embeds"].pop(gid_s, None)

            _write(op)

    # =====================
    # REACTIONS
    # =====================

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

        return (
            cache["runtime"]["reaction_cache"].get(mid_s)
            or cache["reactions"].get(mid_s)
        )

    @staticmethod
    async def del_reaction(mid: int):
        async with _lock:

            def op(cache):
                mid_s = str(mid)
                cache["reactions"].pop(mid_s, None)
                cache["runtime"]["reaction_cache"].pop(mid_s, None)

            _write(op)

    # =====================
    # UI STATE
    # =====================

    @staticmethod
    async def set_ui(key: str, data: dict):
        async with _lock:

            def op(cache):
                cache["ui"][key] = data

            _write(op)

    @staticmethod
    async def get_ui(key: str):
        cache = _get()
        return cache["ui"].get(key)

    @staticmethod
    async def del_ui(key: str):
        async with _lock:

            def op(cache):
                cache["ui"].pop(key, None)

            _write(op)

    # =====================
    # RUNTIME
    # =====================

    @staticmethod
    async def set_rt(key: str, data: dict):
        async with _lock:

            def op(cache):
                cache["runtime"][key] = data

            _write(op)

    @staticmethod
    async def get_rt(key: str):
        cache = _get()
        return cache["runtime"].get(key)

    @staticmethod
    async def clear_rt():
        async with _lock:

            def op(cache):
                cache["runtime"] = {
                    "reaction_cache": {},
                    "message_cache": {}
                }

            _write(op)

    # =====================
    # RESYNC
    # =====================

    @staticmethod
    async def resync():
        """
        cache_manager already handles reload + flush
        keep for interface compatibility
        """
        return True

    @staticmethod
    async def force_resync():
        """
        force reload from disk into memory layer
        """
        load(FILE_KEY)
        return True
