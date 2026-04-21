import asyncio
import json
import os
import time
import copy
from typing import Dict, Any

# =========================
# MEMORY CORE
# =========================

_cache: Dict[str, Dict[str, Any]] = {}
_dirty_keys: set[str] = set()

_lock = asyncio.Lock()
_flush_task = None
_started = False

DATA_DIR = "data"

FLUSH_INTERVAL = 5  # seconds
BACKUP_INTERVAL = 60  # seconds

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

    # backup trước khi ghi
    if os.path.exists(path):
        try:
            backup_path = path + ".bak"
            with open(path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except:
            pass

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(tmp, path)


# =========================
# INIT SYSTEM
# =========================

def _init_key(key: str):
    if key not in _cache:
        _cache[key] = _load_file(key)


# =========================
# PUBLIC API
# =========================

def load(key: str) -> dict:
    """
    Get cache (RAM-first)
    """
    if key not in _cache:
        _init_key(key)

    return _cache[key]


def mark_dirty(key: str):
    """
    Mark key as changed -> will be flushed
    """
    _dirty_keys.add(key)
    _ensure_loop()


# =========================
# FLUSH ENGINE
# =========================

async def _flush_worker():
    global _last_flush_time

    while True:
        try:
            await asyncio.sleep(FLUSH_INTERVAL)

            if not _dirty_keys:
                continue

            async with _lock:
                keys = list(_dirty_keys)
                _dirty_keys.clear()

                for key in keys:
                    if key in _cache:
                        _write_file(key, _cache[key])

                _last_flush_time = time.time()

        except Exception as e:
            print("[CACHE FLUSH ERROR]", e)


# =========================
# BACKUP SAFETY LOOP
# =========================

async def _backup_worker():
    while True:
        try:
            await asyncio.sleep(BACKUP_INTERVAL)

            async with _lock:
                for key, data in _cache.items():
                    backup_path = _file_path(key) + ".auto.bak"
                    try:
                        with open(backup_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    except:
                        pass

        except Exception as e:
            print("[CACHE BACKUP ERROR]", e)


# =========================
# LOOP STARTER
# =========================

def _ensure_loop():
    global _started, _flush_task

    if _started:
        return

    try:
        loop = asyncio.get_running_loop()

        _flush_task = loop.create_task(_flush_worker())
        loop.create_task(_backup_worker())

        _started = True

    except RuntimeError:
        # event loop chưa chạy
        pass


# =========================
# OPTIONAL UTIL
# =========================

def force_flush():
    """
    Force write everything immediately
    """
    for key in list(_cache.keys()):
        if key in _cache:
            _write_file(key, _cache[key])


def get_status():
    return {
        "cached_keys": len(_cache),
        "dirty_keys": len(_dirty_keys),
        "last_flush": _last_flush_time
    }
