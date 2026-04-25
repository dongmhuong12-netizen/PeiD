import asyncio
import json
import os
import time
import copy
import shutil
from typing import Dict, Any

_cache: Dict[str, Dict[str, Any]] = {}
_dirty_keys: set[str] = set()

_lock = asyncio.Lock()
_started = False

DATA_DIR = "data"
FLUSH_INTERVAL = 5  # Kiểm tra dirty định kỳ
BACKUP_INTERVAL = 300 # 5 phút backup một lần

_last_flush_time = 0

# =========================
# FILE HELPERS (Tiêu chuẩn an toàn cao)
# =========================

def _file_path(key: str):
    return os.path.join(DATA_DIR, f"{key}.json")

def _ensure_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def _load_file(key: str):
    path = _file_path(key)
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[DISK READ ERROR] {key}: {e}", flush=True)
        return {}

def _write_file_sync(key: str, data: dict):
    """Ghi file an toàn (Atomic Write)"""
    _ensure_dir()
    path = _file_path(key)
    tmp = path + ".tmp"

    if os.path.exists(path):
        try:
            bak_path = path + ".bak"
            shutil.copy2(path, bak_path)
        except:
            pass

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[DISK WRITE ERROR] {key}: {e}", flush=True)

# =========================
# PUBLIC API
# =========================

def load(key: str) -> dict:
    if key not in _cache:
        _cache[key] = _load_file(key)
    return copy.deepcopy(_cache[key])

def get_raw(key: str) -> dict:
    if key not in _cache:
        _cache[key] = _load_file(key)
    return _cache[key]

def mark_dirty(key: str):
    _dirty_keys.add(key)
    _ensure_loop()

def update(key: str, value: dict):
    _cache[key] = value
    mark_dirty(key)

async def save(key: str):
    """
    ÉP LƯU NGAY LẬP TỨC (Dùng cho các lệnh quan trọng như Set Role).
    Không cần chờ 5 giây của flush worker.
    """
    if key in _cache:
        data = copy.deepcopy(_cache[key])
        await asyncio.to_thread(_write_file_sync, key, data)
        if key in _dirty_keys:
            _dirty_keys.remove(key)
        print(f"[CACHE] Đã ép lưu khẩn cấp: {key}.json", flush=True)

# =========================
# FLUSH ENGINE
# =========================

async def _flush_worker():
    global _last_flush_time
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)
        if not _dirty_keys:
            continue

        async with _lock:
            keys_to_flush = list(_dirty_keys)
            _dirty_keys.clear()

            for key in keys_to_flush:
                data = _cache.get(key)
                if data is not None:
                    await asyncio.to_thread(_write_file_sync, key, copy.deepcopy(data))

            _last_flush_time = time.time()
            print(f"[CACHE] Đã tự động lưu {len(keys_to_flush)} tệp.", flush=True)

async def _backup_worker():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        async with _lock:
            for key, data in _cache.items():
                if data:
                    await asyncio.to_thread(_write_file_sync, f"{key}.auto", data)

# =========================
# CONTROL CENTER
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
    """Ghi đĩa khẩn cấp toàn bộ RAM (Dùng khi tắt Bot)"""
    print("[CACHE] Bắt đầu ghi khẩn cấp toàn bộ dữ liệu...", flush=True)
    # Ghi cả những thứ đang dirty và cả những thứ đang có trong RAM cho chắc chắn
    for key, data in _cache.items():
        _write_file_sync(key, data)
    print("[CACHE] Toàn bộ dữ liệu đã được bảo vệ.", flush=True)
