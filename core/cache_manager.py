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
FLUSH_INTERVAL = 5  # 5 giây kiểm tra dirty một lần
BACKUP_INTERVAL = 300 # 5 phút backup một lần để tránh tốn CPU

_last_flush_time = 0

# =========================
# FILE HELPERS (TIÊU CHUẨN 100K+)
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
    """Hàm ghi file đồng bộ, chạy trong Thread riêng để không block Event Loop"""
    _ensure_dir()
    path = _file_path(key)
    tmp = path + ".tmp"

    # Backup an toàn trước khi ghi
    if os.path.exists(path):
        try:
            bak_path = path + ".bak"
            shutil.copy2(path, bak_path)
        except:
            pass

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            # indent=2 giúp con người dễ đọc, ensure_ascii=False hỗ trợ tiếng Việt
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # os.replace là thao tác nguyên tử (Atomic), cực kỳ an toàn
        os.replace(tmp, path)
    except Exception as e:
        print(f"[DISK WRITE ERROR] {key}: {e}", flush=True)

# =========================
# PUBLIC API (Giao diện điều khiển)
# =========================

def load(key: str) -> dict:
    """Nạp dữ liệu vào RAM và trả về bản sao để tránh can thiệp nhầm"""
    if key not in _cache:
        _cache[key] = _load_file(key)
    return copy.deepcopy(_cache[key])

def get_raw(key: str) -> dict:
    """Lấy reference trực tiếp từ RAM (Dùng cho State để xử lý tốc độ cao)"""
    if key not in _cache:
        _cache[key] = _load_file(key)
    return _cache[key]

def mark_dirty(key: str):
    """Đánh dấu dữ liệu đã thay đổi, cần được bơm xuống đĩa"""
    _dirty_keys.add(key)
    _ensure_loop()

def update(key: str, value: dict):
    """Cập nhật toàn bộ và đánh dấu ghi đĩa"""
    _cache[key] = value
    mark_dirty(key)

# =========================
# FLUSH ENGINE (Bơm máu dữ liệu)
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
                    # Đẩy sang Thread riêng để Bot không bị giật lag (Freeze)
                    await asyncio.to_thread(_write_file_sync, key, copy.deepcopy(data))

            _last_flush_time = time.time()
            print(f"[CACHE] Đã lưu {len(keys_to_flush)} tệp xuống đĩa cứng.", flush=True)

async def _backup_worker():
    """Tự động sao lưu định kỳ để chống mất dữ liệu"""
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        async with _lock:
            active_keys = list(_cache.keys())
            for key in active_keys:
                data = _cache.get(key)
                if data:
                    await asyncio.to_thread(_write_file_sync, f"{key}.auto", data)
            print(f"[BACKUP] Đã tự động sao lưu {len(active_keys)} mô-đun.", flush=True)

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
        # Nếu chưa có loop đang chạy, sẽ được kích hoạt lại ở lần call sau
        pass

def force_flush():
    """Ép ghi toàn bộ ngay lập tức (Dùng khi Render tắt Bot)"""
    print("[CACHE] Đang thực hiện ghi khẩn cấp xuống đĩa...", flush=True)
    for key, data in _cache.items():
        _write_file_sync(key, data)
    print("[CACHE] Ghi khẩn cấp hoàn tất.", flush=True)

def get_status():
    return {
        "cached_keys": list(_cache.keys()),
        "dirty_keys": list(_dirty_keys),
        "last_flush": time.ctime(_last_flush_time) if _last_flush_time > 0 else "Never"
    }
