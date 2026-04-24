import asyncio
import json
import os
import time
import copy
from typing import Dict, Any

_cache: Dict[str, Dict[str, Any]] = {}
_dirty_keys: set[str] = set()

_lock = asyncio.Lock()
_started = False

DATA_DIR = "data"

FLUSH_INTERVAL = 5
BACKUP_INTERVAL = 60

_last_flush_time = 0


# =========================
# FILE HELPERS (Tối ưu Thread-safe)
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


def _write_file_sync(key: str, data: dict):
    """Hàm ghi file đồng bộ, sẽ được chạy trong Thread riêng"""
    _ensure_dir()
    path = _file_path(key)
    tmp = path + ".tmp"

    # Backup an toàn
    if os.path.exists(path):
        try:
            bak_path = path + ".bak"
            # Dùng phương thức copy nhanh của hệ điều hành
            import shutil
            shutil.copy2(path, bak_path)
        except:
            pass

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False) # Hỗ trợ tiếng Việt tốt hơn
        os.replace(tmp, path)
    except Exception as e:
        print(f"[DISK WRITE ERROR] {key}: {e}")


# =========================
# INIT
# =========================

def _init_key(key: str):
    if key in _cache:
        return
    _cache[key] = _load_file(key)


# =========================
# PUBLIC API
# =========================

def load(key: str) -> dict:
    """Trả về bản sao dữ liệu từ RAM."""
    if key not in _cache:
        _init_key(key)
    return copy.deepcopy(_cache[key])


def get_raw(key: str) -> dict:
    """Trả về bản gốc trong RAM để sửa trực tiếp (Cực nhanh)"""
    if key not in _cache:
        _init_key(key)
    return _cache[key]


def mark_dirty(key: str):
    """Đánh dấu key cần được ghi xuống đĩa"""
    _dirty_keys.add(key)
    _ensure_loop()


def update(key: str, value: dict):
    """Cập nhật toàn bộ data cho một key"""
    if key not in _cache:
        _init_key(key)
    _cache[key] = value
    mark_dirty(key)


# =========================
# FLUSH ENGINE (Async Tối ưu)
# =========================

async def _flush_worker():
    global _last_flush_time
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)
        if not _dirty_keys:
            continue

        async with _lock:
            keys = list(_dirty_keys)
            _dirty_keys.clear()

            for key in keys:
                data = _cache.get(key)
                if data is not None:
                    # TIÊU CHUẨN 100K+: Đẩy việc ghi file sang Thread riêng
                    # Giúp Event Loop không bị block, Bot không bị lag.
                    await asyncio.to_thread(_write_file_sync, key, copy.deepcopy(data))

            _last_flush_time = time.time()


async def _backup_worker():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        async with _lock:
            for key, data in _cache.items():
                try:
                    backup_path = _file_path(key) + ".auto.bak"
                    # Ghi backup cũng dùng thread để an toàn
                    await asyncio.to_thread(_write_file_sync, f"{key}.auto", data)
                except:
                    pass


# =========================
# CONTROL
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


def force_flush():
    """Ép ghi toàn bộ cache xuống đĩa ngay lập tức (Dùng khi shutdown)"""
    for key, data in _cache.items():
        _write_file_sync(key, data)


def get_status():
    return {
        "cached_keys": len(_cache),
        "dirty_keys": len(_dirty_keys),
        "last_flush": _last_flush_time
    }
