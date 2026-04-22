import asyncio
import json
import os
import time
import copy
from typing import Dict, Any

# =========================
# MEMORY CORE (FIXED ARCH)
# =========================

_cache: Dict[str, Dict[str, Any]] = {}
_dirty_keys: set[str] = set()

_lock = asyncio.Lock()
_started = False

DATA_DIR = "data"

FLUSH_INTERVAL = 5
BACKUP_INTERVAL = 60

_last_flush_time = 0


# =========================
# FILE HELPERS
# =========================

def _file_path(key: str):
    return os.path.join(DATA_DIR, f"{key}.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_file(key: str):
    path = _file_path(key)

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}


def _write_file(key: str, data: dict):
    _ensure_dir()

    path = _file_path(key)
    tmp = path + ".tmp"

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as src:
                old = src.read()
            with open(path + ".bak", "w", encoding="utf-8") as dst:
                dst.write(old)
        except:
            pass

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(tmp, path)


# =========================
# INIT
# =========================

def _init_key(key: str):
    if key not in _cache:
        _cache[key] = _load_file(key)


# =========================
# PUBLIC API (FIXED CORE)
# =========================

def load(key: str) -> dict:
    """
    SAFE SNAPSHOT READ
    FIX:
    - vẫn deepcopy nhưng đảm bảo schema runtime không bị phá
    """
    if key not in _cache:
        _init_key(key)

    return copy.deepcopy(_cache[key])


def get_raw(key: str) -> dict:
    """
    INTERNAL MUTABLE ACCESS
    FIX:
    - đảm bảo init + schema luôn tồn tại (QUAN TRỌNG CHO STATE)
    """
    if key not in _cache:
        _init_key(key)

    # 🔥 FIX CRITICAL: guarantee schema container tồn tại
    if isinstance(_cache[key], dict):
        _cache[key].setdefault("runtime", {})
        _cache[key].setdefault("embeds", {})
        _cache[key].setdefault("reactions", {})
        _cache[key].setdefault("ui", {})

    return _cache[key]


def mark_dirty(key: str):
    _dirty_keys.add(key)
    _ensure_loop()


def update(key: str, value: dict):
    """
    ATOMIC REPLACE SAFE
    FIX:
    - không deepcopy input nữa (tránh double-copy bug sender/state mismatch)
    """
    if key not in _cache:
        _init_key(key)

    _cache[key] = value
    _dirty_keys.add(key)
    _ensure_loop()


# =========================
# FLUSH ENGINE
# =========================

async def _flush_worker():
    global _last_flush_time

    while True:
        await asyncio.sleep(FLUSH_INTERVAL)

        if not _dirty_keys:
            continue

        try:
            async with _lock:
                keys = list(_dirty_keys)
                _dirty_keys.clear()

                for key in keys:
                    data = _cache.get(key)
                    if data is not None:
                        _write_file(key, data)

                _last_flush_time = time.time()

        except Exception as e:
            print("[CACHE FLUSH ERROR]", e)


# =========================
# BACKUP
# =========================

async def _backup_worker():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)

        try:
            async with _lock:
                for key, data in _cache.items():
                    try:
                        backup_path = _file_path(key) + ".auto.bak"
                        with open(backup_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    except:
                        pass
        except Exception as e:
            print("[CACHE BACKUP ERROR]", e)


# =========================
# LOOP START
# =========================

def _ensure_loop():
    global _started

    if _started:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_flush_worker())
        loop.create_task(_backup_worker())
        _started = True

    except RuntimeError:
        pass


# =========================
# UTIL
# =========================

def force_flush():
    for key, data in list(_cache.items()):
        _write_file(key, data)


def get_status():
    return {
        "cached_keys": len(_cache),
        "dirty_keys": len(_dirty_keys),
        "last_flush": _last_flush_time
    }
