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
# CORE UTIL
# =========================

def _ensure_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "version": 1,
                "embeds": {},
                "reactions": {},
                "ui": {},
                "runtime": {}
            }, f, indent=2)


def _load_file() -> Dict[str, Any]:
    _ensure_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": 1,
            "embeds": {},
            "reactions": {},
            "ui": {},
            "runtime": {}
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
# CACHE LAYER (10/10 UPGRADE)
# =========================

def _load_cache():
    global _cache, _cache_loaded

    if not _cache_loaded:
        _cache = _load_file()
        _cache_loaded = True


def _sync_cache():
    global _cache
    _cache = _load_file()


def _commit():
    global _cache
    if _cache is not None:
        _write_file(_cache)


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
            _load_cache()
            _cache["embeds"].setdefault(str(gid), {})
            _cache["embeds"][str(gid)][name] = data
            _commit()

    @staticmethod
    async def get_embed(gid: int, name: str):
        _load_cache()
        return _cache["embeds"].get(str(gid), {}).get(name)

    @staticmethod
    async def del_embed(gid: int, name: str):
        async with _lock:
            _load_cache()
            g = _cache["embeds"].get(str(gid), {})
            g.pop(name, None)
            _cache["embeds"][str(gid)] = g
            _commit()


    # =====================
    # REACTIONS
    # =====================

    @staticmethod
    async def set_reaction(mid: int, data: dict):
        async with _lock:
            _load_cache()
            _cache["reactions"][str(mid)] = data
            _commit()

    @staticmethod
    async def get_reaction(mid: int):
        _load_cache()
        return _cache["reactions"].get(str(mid))

    @staticmethod
    async def del_reaction(mid: int):
        async with _lock:
            _load_cache()
            _cache["reactions"].pop(str(mid), None)
            _commit()


    # =====================
    # UI STATE
    # =====================

    @staticmethod
    async def set_ui(key: str, data: dict):
        async with _lock:
            _load_cache()
            _cache["ui"][key] = data
            _commit()

    @staticmethod
    async def get_ui(key: str):
        _load_cache()
        return _cache["ui"].get(key)

    @staticmethod
    async def del_ui(key: str):
        async with _lock:
            _load_cache()
            _cache["ui"].pop(key, None)
            _commit()


    # =====================
    # RUNTIME CACHE
    # =====================

    @staticmethod
    async def set_rt(key: str, data: dict):
        async with _lock:
            _load_cache()
            _cache["runtime"][key] = data
            _commit()

    @staticmethod
    async def get_rt(key: str):
        _load_cache()
        return _cache["runtime"].get(key)

    @staticmethod
    async def clear_rt():
        async with _lock:
            _load_cache()
            _cache["runtime"] = {}
            _commit()


    # =====================
    # FORCE RESYNC (WAKE SYSTEM HOOK)
    # =====================

    @staticmethod
    async def resync():
        """reload toàn bộ state từ disk (dùng khi bot restart)"""
        global _cache
        async with _lock:
            _cache = _load_file()
