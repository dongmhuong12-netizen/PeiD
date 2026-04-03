import json
import os
import asyncio
import tempfile
import shutil
import copy

DATA_FILE = "data/booster_levels.json"
_lock = asyncio.Lock()


# ==============================
# INTERNAL
# ==============================

def _ensure_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf8") as f:
            json.dump({}, f)


def _load():
    _ensure_file()

    try:
        with open(DATA_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save(data):
    directory = os.path.dirname(DATA_FILE)

    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=directory,
        encoding="utf8"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        temp_name = tmp.name

    shutil.move(temp_name, DATA_FILE)


# ==============================
# NORMALIZE LEVELS
# ==============================

def _normalize_levels(levels: list):
    normalized = []

    for lvl in levels:
        normalized.append({
            "role": lvl.get("role"),
            "days": lvl.get("days")
        })

    return normalized


# ==============================
# GET CONFIG
# ==============================

async def get_guild_config(guild_id: int):
    async with _lock:
        data = _load()
        config = data.get(str(guild_id))

        if not config:
            return {
                "booster_role": None,
                "channel": None,
                "levels": []
            }

        config = copy.deepcopy(config)
        levels = config.get("levels")

        # migrate old dict format
        if isinstance(levels, dict):
            new_levels = []

            for _, value in sorted(
                levels.items(),
                key=lambda x: int(x[0])
            ):
                new_levels.append({
                    "role": value.get("role"),
                    "days": value.get("days")
                })

            config["levels"] = _normalize_levels(new_levels)
            data[str(guild_id)] = config
            _save(data)

        if "booster_role" not in config:
            config["booster_role"] = None

        if "channel" not in config:
            config["channel"] = None

        if not isinstance(config.get("levels"), list):
            config["levels"] = []

        config["levels"] = _normalize_levels(config["levels"])
        return config


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):
    async with _lock:
        data = _load()

        config = copy.deepcopy(config)
        levels = config.get("levels", [])
        config["levels"] = _normalize_levels(levels)

        data[str(guild_id)] = config
        _save(data)


# ==============================
# SET BOOSTER ROLE
# ==============================

async def set_booster_role(guild_id: int, role_id: int):
    config = await get_guild_config(guild_id)
    config["booster_role"] = role_id
    await save_guild_config(guild_id, config)


# ==============================
# GET LEVELS
# ==============================

async def get_levels(guild_id: int):
    config = await get_guild_config(guild_id)
    return config.get("levels", [])


# ==============================
# SAVE LEVELS
# ==============================

async def save_levels(guild_id: int, levels: list):
    config = await get_guild_config(guild_id)
    config["levels"] = _normalize_levels(levels)
    await save_guild_config(guild_id, config)


# ==============================
# CLEAR ALL
# ==============================

async def clear_levels(guild_id: int):
    config = await get_guild_config(guild_id)
    config["levels"] = []
    await save_guild_config(guild_id, config)
