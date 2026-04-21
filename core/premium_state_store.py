import json
import os
import asyncio
import tempfile
import shutil
from typing import Dict, Any

# =========================
# FILE PATH
# =========================

DATA_FILE = "data/premium_state.json"
_lock = asyncio.Lock()


# =========================
# INTERNAL UTIL
# =========================

def _ensure_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "embeds": {},
                "reactions": {},
                "ui_state": {},
                "runtime": {}
            }, f, indent=2)


def _load_all() -> Dict[str, Any]:
    _ensure_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "embeds": {},
            "reactions": {},
            "ui_state": {},
            "runtime": {}
        }


def _atomic_save(data: Dict[str, Any]):
    os.makedirs("data", exist_ok=True)

    directory = os.path.dirname(DATA_FILE)

    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=directory,
        encoding="utf-8"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        temp_name = tmp.name

    shutil.move(temp_name, DATA_FILE)


# =========================
# CORE STORE CLASS
# =========================

class PremiumStateStore:

    # =========================================================
    # EMBED MAPPING
    # guild_id -> embed_name -> data
    # =========================================================

    @staticmethod
    async def set_embed(guild_id: int, name: str, data: dict):
        async with _lock:
            all_data = _load_all()

            all_data["embeds"].setdefault(str(guild_id), {})
            all_data["embeds"][str(guild_id)][name] = data

            _atomic_save(all_data)

    @staticmethod
    async def get_embed(guild_id: int, name: str):
        all_data = _load_all()
        return all_data.get("embeds", {}).get(str(guild_id), {}).get(name)

    @staticmethod
    async def delete_embed(guild_id: int, name: str):
        async with _lock:
            all_data = _load_all()

            guild_data = all_data.get("embeds", {}).get(str(guild_id), {})

            if name in guild_data:
                del guild_data[name]

            all_data["embeds"][str(guild_id)] = guild_data

            _atomic_save(all_data)


    # =========================================================
    # REACTION MAPPING
    # message_id -> reaction config
    # =========================================================

    @staticmethod
    async def set_reaction(message_id: int, data: dict):
        async with _lock:
            all_data = _load_all()
            all_data["reactions"][str(message_id)] = data
            _atomic_save(all_data)

    @staticmethod
    async def get_reaction(message_id: int):
        all_data = _load_all()
        return all_data.get("reactions", {}).get(str(message_id))

    @staticmethod
    async def delete_reaction(message_id: int):
        async with _lock:
            all_data = _load_all()

            if str(message_id) in all_data.get("reactions", {}):
                del all_data["reactions"][str(message_id)]

            _atomic_save(all_data)


    # =========================================================
    # UI STATE (runtime memory backup)
    # ONLY USE FOR RESTORE AFTER RESTART
    # =========================================================

    @staticmethod
    async def set_ui_state(key: str, data: dict):
        async with _lock:
            all_data = _load_all()
            all_data["ui_state"][key] = data
            _atomic_save(all_data)

    @staticmethod
    async def get_ui_state(key: str):
        all_data = _load_all()
        return all_data.get("ui_state", {}).get(key)

    @staticmethod
    async def delete_ui_state(key: str):
        async with _lock:
            all_data = _load_all()

            if key in all_data.get("ui_state", {}):
                del all_data["ui_state"][key]

            _atomic_save(all_data)


    # =========================================================
    # RUNTIME CACHE (optional future use)
    # =========================================================

    @staticmethod
    async def set_runtime(key: str, data: dict):
        async with _lock:
            all_data = _load_all()
            all_data["runtime"][key] = data
            _atomic_save(all_data)

    @staticmethod
    async def get_runtime(key: str):
        all_data = _load_all()
        return all_data.get("runtime", {}).get(key)

    @staticmethod
    async def clear_runtime():
        async with _lock:
            all_data = _load_all()
            all_data["runtime"] = {}
            _atomic_save(all_data)
