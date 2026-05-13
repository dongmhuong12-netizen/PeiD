import asyncio
import copy
from typing import Dict, Any

# [TRÍ NHỚ ĐÃ BÓC TÁCH] Chỉ giữ lại dictionary trong RAM, gỡ bỏ toàn bộ logic liên quan đến file vật lý
_cache: Dict[str, Dict[str, Any]] = {}
_dirty_keys: set[str] = set()

_lock = asyncio.Lock()
_started = False

# =========================
# PUBLIC API (Giữ nguyên Interface để không hỏng Import)
# =========================

def load(key: str) -> dict:
    """Lấy dữ liệu từ RAM. Nếu không có trả về dict rỗng."""
    if key not in _cache:
        _cache[key] = {}
    return copy.deepcopy(_cache[key])

def get_raw(key: str) -> dict:
    """Lấy reference trực tiếp từ RAM."""
    if key not in _cache:
        _cache[key] = {}
    return _cache[key]

def mark_dirty(key: str):
    """Giữ nguyên hàm để các module khác không bị lỗi, nhưng không còn ghi đĩa."""
    _dirty_keys.add(key)

def update(key: str, value: dict):
    """Cập nhật dữ liệu trong RAM."""
    _cache[key] = value
    mark_dirty(key)

async def save(key: str):
    """
    [TRÍ NHỚ ĐÃ BÓC TÁCH] 
    Vô hiệu hóa việc ép lưu xuống đĩa. MongoDB sẽ tiếp quản logic này.
    """
    if key in _dirty_keys:
        _dirty_keys.remove(key)
    # print(f"[CACHE] Stateless Mode: Lệnh lưu '{key}' đã được chuyển tiếp.", flush=True)

# =========================
# FLUSH ENGINE (VÔ HIỆU HÓA)
# =========================

async def _flush_worker():
    """Hàm chạy nền nhưng không còn thực hiện ghi file."""
    while True:
        await asyncio.sleep(3600) # Ngủ dài để không tốn tài nguyên

async def _backup_worker():
    """Vô hiệu hóa hoàn toàn việc backup file cục bộ."""
    while True:
        await asyncio.sleep(3600)

# =========================
# CONTROL CENTER
# =========================

def _ensure_loop():
    """Giữ lại để đảm bảo cấu trúc bot không thay đổi."""
    global _started
    if _started:
        return
    _started = True

def force_flush():
    """
    [TRÍ NHỚ ĐÃ BÓC TÁCH] 
    Không còn ghi khẩn cấp vào tệp tin khi tắt Bot.
    """
    print("[CACHE] Stateless Mode: Toàn bộ dữ liệu RAM đã được giải phóng.", flush=True)
