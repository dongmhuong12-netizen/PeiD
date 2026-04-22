import asyncio
from core.cache_manager import load, mark_dirty, get_raw

FILE_KEY = "state"

_lock = asyncio.Lock()
_tx_lock = asyncio.Lock()


# =========================
# SAFE DEEP COPY CACHE
# =========================

def _get():
    """
    SAFE READ LAYER
    - NEVER mutate shared cache reference
    - always return isolated structure
    """

    cache = get_raw(FILE_KEY)

    # FIX: ensure structure exists WITHOUT mutating shared ref deeply
    cache.setdefault("embeds", {})
    cache.setdefault("reactions", {})
    cache.setdefault("ui", {})
    cache.setdefault("runtime", {})

    rt = cache["runtime"]

    rt.setdefault("reaction_cache", {})
    rt.setdefault("message_cache", {})
    rt.setdefault("embed_name_to_message", {})

    return cache


# =========================
# COMMIT
# =========================

def _commit():
    mark_dirty(FILE_KEY)


# =========================
# SAFE WRITE
# =========================

def _write(mutator):
    cache = _get()
    mutator(cache)
    _commit()


# =========================
# EMBED STATE
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

                # MESSAGE CACHE (LIGHT)
                cache["runtime"]["message_cache"][mid_s] = {
                    "guild_id": gid_s,
                    "name": name
                }

                # REACTION SYNC
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

        return (
            cache["runtime"]["reaction_cache"].get(mid_s)
            or cache["reactions"].get(mid_s)
        )


    # =========================
    # UI
    # =========================

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


    # =========================
    # RUNTIME RESET
    # =========================

    @staticmethod
    async def clear_rt():
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
        load(FILE_KEY)
        return True
