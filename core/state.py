import asyncio
from core.cache_manager import load, mark_dirty, get_raw

FILE_KEY = "state"

_lock = asyncio.Lock()
_tx_lock = asyncio.Lock()


# =========================
# INTERNAL SAFE GET
# =========================

def _get():
    """
    SAFE READ LAYER (FIXED)
    - DO NOT mutate shared cache reference
    - always isolate runtime structure safely
    """

    cache = get_raw(FILE_KEY)

    # 🔥 FIX: avoid mutating shared reference directly
    if "embeds" not in cache:
        cache["embeds"] = {}
    if "reactions" not in cache:
        cache["reactions"] = {}
    if "ui" not in cache:
        cache["ui"] = {}
    if "runtime" not in cache:
        cache["runtime"] = {}

    rt = cache["runtime"]

    if "reaction_cache" not in rt:
        rt["reaction_cache"] = {}
    if "message_cache" not in rt:
        rt["message_cache"] = {}
    if "embed_name_to_message" not in rt:
        rt["embed_name_to_message"] = {}

    cache["runtime"] = rt

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
# EMBEDS
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
    # ATOMIC PIPELINE CORE (FIXED)
    # =========================

    @staticmethod
    async def atomic_embed_register(
        gid: int,
        name: str,
        message_id: int,
        reaction_data: dict | None = None
    ):

        async with _tx_lock:

            def op(cache):
                gid_s = str(gid)
                mid_s = str(message_id)

                # =========================
                # NAME → MESSAGE (SOURCE OF TRUTH)
                # =========================
                cache["runtime"]["embed_name_to_message"].setdefault(gid_s, {})
                cache["runtime"]["embed_name_to_message"][gid_s][name] = mid_s

                # =========================
                # FIX: message_cache chỉ giữ mapping nhẹ, không metadata UI
                # =========================
                cache["runtime"]["message_cache"][mid_s] = {
                    "guild_id": gid_s,
                    "name": name
                }

                # =========================
                # REACTION SYNC
                # =========================
                if reaction_data:
                    cache["reactions"][mid_s] = reaction_data
                    cache["runtime"]["reaction_cache"][mid_s] = reaction_data

            _write(op)

    @staticmethod
    async def get_embed_message(gid: int, name: str):
        cache = _get()

        return (
            cache["runtime"]["embed_name_to_message"]
            .get(str(gid), {})
            .get(name)
        )

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

    @staticmethod
    async def del_reaction(mid: int):
        async with _lock:

            def op(cache):
                mid_s = str(mid)
                cache["reactions"].pop(mid_s, None)
                cache["runtime"]["reaction_cache"].pop(mid_s, None)

            _write(op)

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

    @staticmethod
    async def del_ui(key: str):
        async with _lock:

            def op(cache):
                cache["ui"].pop(key, None)

            _write(op)

    # =========================
    # RUNTIME
    # =========================

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
                    "message_cache": {},
                    "embed_name_to_message": {}
                }

            _write(op)

    # =========================
    # RESYNC
    # =========================

    @staticmethod
    async def resync():
        return True

    @staticmethod
    async def force_resync():
        load(FILE_KEY)
        return True
