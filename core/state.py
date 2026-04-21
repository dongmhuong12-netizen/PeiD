import json
import os
import asyncio
import tempfile
import shutil
from typing import Dict, Any

DATA_FILE = "data/state.json"

_lock = asyncio.Lock()
_cache: Dict[str, Any] | None = None
_cache_loaded = False


# =========================
# CORE FILE OPS
# =========================

def _ensure_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        default = {
            "version": 1,

            # embed system
            "embeds": {},

            # reaction role system (MESSAGE_ID → CONFIG)
            "reactions": {},

            # embed UI / editor state
            "ui": {},

            # runtime cache (FAST MEMORY ONLY - NOT RELIABLY PERSISTED ACROSS INSTANCES)
            "runtime": {
                "reaction_cache": {},
                "message_cache": {}
            }
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)


def _load_file() -> Dict[str, Any]:
    _ensure_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError()

            data.setdefault("version", 1)
            data.setdefault("embeds", {})
            data.setdefault("reactions", {})
            data.setdefault("ui", {})

            data.setdefault("runtime", {})
            data["runtime"].setdefault("reaction_cache", {})
            data["runtime"].setdefault("message_cache", {})

            return data

    except Exception:
        return {
            "version": 1,
            "embeds": {},
            "reactions": {},
            "ui": {},
            "runtime": {
                "reaction_cache": {},
                "message_cache": {}
            }
        }


def _write_file(data: Dict[str, Any]):
    os.makedirs("data", exist_ok=True)

    directory = os.path.dirname(DATA_FILE)

    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=directory,
        encoding="utf-8"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        temp = tmp.name

    shutil.move(temp, DATA_FILE)


# =========================
# CACHE LAYER (FIXED SAFETY)
# =========================

def _load_cache():
    global _cache, _cache_loaded
    if not _cache_loaded:
        _cache = _load_file()
        _cache_loaded = True


def _force_reload():
    """SAFE RESYNC for restart / external update cases"""
    global _cache, _cache_loaded
    _cache = _load_file()
    _cache_loaded = True


def _commit():
    global _cache
    if _cache is not None:
        _write_file(_cache)


def _get():
    _load_cache()
    return _cache if _cache is not None else {}


# =========================
# PUBLIC API
# =========================

class State:

    # =====================
    # EMBEDS
    # =====================

    @staticmethod
    async def set_embed(gid: int, name: str, data: dict):
        async with _lock:
            cache = _get()
            cache["embeds"].setdefault(str(gid), {})
            cache["embeds"][str(gid)][name] = data
            _commit()

    @staticmethod
    async def get_embed(gid: int, name: str):
        cache = _get()
        return cache["embeds"].get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:
            cache = _get()
            cache["embeds"].get(str(gid), {}).pop(name, None)
            _commit()

    # =====================
    # REACTIONS
    # =====================

    @staticmethod
    async def set_reaction(mid: int, data: dict):
        async with _lock:
            cache = _get()
            cache["reactions"][str(mid)] = data

            cache["runtime"]["reaction_cache"][str(mid)] = data

            _commit()

    @staticmethod
    async def get_reaction(mid: int):
        cache = _get()

        rt = cache["runtime"].get("reaction_cache", {}).get(str(mid))
        if rt:
            return rt

        return cache["reactions"].get(str(mid))

    @staticmethod
    async def del_reaction(mid: int):
        async with _lock:
            cache = _get()
            cache["reactions"].pop(str(mid), None)
            cache["runtime"]["reaction_cache"].pop(str(mid), None)
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
    # RUNTIME CACHE (FIXED SEMANTIC)
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
    # SAFE RESYNC (FIXED FOR SCALE)
    # =====================

    @staticmethod
    async def resync():
        global _cache
        async with _lock:
            _cache = _load_file()
            global _cache_loaded
            _cache_loaded = True

    @staticmethod
    async def force_resync():
        """Use when external systems may modify file"""
        async with _lock:
            _force_reload()
