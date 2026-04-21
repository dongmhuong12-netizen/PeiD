import asyncio
import time
import json
import os

CACHE = {}
DIRTY = set()
LOCK = asyncio.Lock()

FLUSH_INTERVAL = 5  # SAFE MODE
_file_map = {}


# =========================
# REGISTER FILES
# =========================

def register(file_key: str, path: str):
    _file_map[file_key] = path

    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)


# =========================
# LOAD
# =========================

def load(file_key: str):
    path = _file_map[file_key]

    if file_key in CACHE:
        return CACHE[file_key]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            CACHE[file_key] = data
            return data
    except:
        CACHE[file_key] = {}
        return {}


# =========================
# MARK DIRTY
# =========================

def mark_dirty(file_key: str):
    DIRTY.add(file_key)


# =========================
# SAVE
# =========================

def save(file_key: str):
    path = _file_map[file_key]
    data = CACHE.get(file_key, {})

    tmp = path + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(tmp, path)


# =========================
# FLUSH LOOP
# =========================

async def flush_loop():
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)

        async with LOCK:
            if not DIRTY:
                continue

            for key in list(DIRTY):
                try:
                    save(key)
                except:
                    pass

                DIRTY.discard(key)
