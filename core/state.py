import asyncio
from core.cache_manager import load, mark_dirty

FILE_KEY = "state"


class State:

    # =====================
    # EMBEDS
    # =====================

    @staticmethod
    async def set_embed(gid: int, name: str, data: dict):
        cache = load(FILE_KEY)

        gid = str(gid)

        if "embeds" not in cache:
            cache["embeds"] = {}

        if gid not in cache["embeds"]:
            cache["embeds"][gid] = {}

        cache["embeds"][gid][name] = data

        mark_dirty(FILE_KEY)

    @staticmethod
    async def get_embed(gid: int, name: str):
        cache = load(FILE_KEY)

        return cache.get("embeds", {}).get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        cache = load(FILE_KEY)

        gid = str(gid)

        if gid in cache.get("embeds", {}):
            cache["embeds"][gid].pop(name, None)

            if not cache["embeds"][gid]:
                cache["embeds"].pop(gid, None)

            mark_dirty(FILE_KEY)

    # =====================
    # REACTIONS
    # =====================

    @staticmethod
    async def set_reaction(mid: int, data: dict):
        cache = load(FILE_KEY)

        mid = str(mid)

        if "reactions" not in cache:
            cache["reactions"] = {}

        cache["reactions"][mid] = data

        if "runtime" not in cache:
            cache["runtime"] = {}

        if "reaction_cache" not in cache["runtime"]:
            cache["runtime"]["reaction_cache"] = {}

        cache["runtime"]["reaction_cache"][mid] = data

        mark_dirty(FILE_KEY)

    @staticmethod
    async def get_reaction(mid: int):
        cache = load(FILE_KEY)

        mid = str(mid)

        rt = cache.get("runtime", {}).get("reaction_cache", {}).get(mid)
        if rt:
            return rt

        return cache.get("reactions", {}).get(mid)

    @staticmethod
    async def del_reaction(mid: int):
        cache = load(FILE_KEY)

        mid = str(mid)

        cache.get("reactions", {}).pop(mid, None)
        cache.get("runtime", {}).get("reaction_cache", {}).pop(mid, None)

        mark_dirty(FILE_KEY)

    # =====================
    # UI STATE
    # =====================

    @staticmethod
    async def set_ui(key: str, data: dict):
        cache = load(FILE_KEY)

        if "ui" not in cache:
            cache["ui"] = {}

        cache["ui"][key] = data

        mark_dirty(FILE_KEY)

    @staticmethod
    async def get_ui(key: str):
        cache = load(FILE_KEY)

        return cache.get("ui", {}).get(key)

    @staticmethod
    async def del_ui(key: str):
        cache = load(FILE_KEY)

        cache.get("ui", {}).pop(key, None)

        mark_dirty(FILE_KEY)

    # =====================
    # RUNTIME CACHE
    # =====================

    @staticmethod
    async def set_rt(key: str, data: dict):
        cache = load(FILE_KEY)

        if "runtime" not in cache:
            cache["runtime"] = {}

        cache["runtime"][key] = data

        mark_dirty(FILE_KEY)

    @staticmethod
    async def get_rt(key: str):
        cache = load(FILE_KEY)

        return cache.get("runtime", {}).get(key)

    @staticmethod
    async def clear_rt():
        cache = load(FILE_KEY)

        cache["runtime"] = {
            "reaction_cache": {},
            "message_cache": {}
        }

        mark_dirty(FILE_KEY)

    # =====================
    # RESYNC (SAFE RELOAD)
    # =====================

    @staticmethod
    async def resync():
        # force reload handled by cache system automatically
        return True

    @staticmethod
    async def force_resync():
        # no-op in phase 2 (cache manager handles consistency)
        return True
