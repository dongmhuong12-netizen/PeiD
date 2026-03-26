import json
import os
import asyncio
import tempfile
import shutil

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

        # migrate old dict -> list (AUTO FIX)
        if isinstance(config.get("levels"), dict):

            levels_dict = config.get("levels", {})

            levels_list = []

            for lvl, value in sorted(
                levels_dict.items(),
                key=lambda x: int(x[0])
            ):
                levels_list.append({
                    "role": value.get("role"),
                    "days": value.get("days")
                })

            config["levels"] = levels_list

            data[str(guild_id)] = config
            _save(data)

        # ensure list
        if "levels" not in config or not isinstance(config["levels"], list):
            config["levels"] = []

        return config


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):

    async with _lock:

        data = _load()

        # safety normalize
        if "levels" not in config or not isinstance(config["levels"], list):
            config["levels"] = []

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
# SAVE LEVELS (MAIN)
# ==============================

async def save_levels(guild_id: int, levels: list):

    config = await get_guild_config(guild_id)

    # remove empty levels
    cleaned = []

    for lvl in levels:
        role = lvl.get("role")
        days = lvl.get("days")

        if role is None or days is None:
            continue

        cleaned.append({
            "role": role,
            "days": days
        })

    config["levels"] = cleaned

    await save_guild_config(guild_id, config)


# ==============================
# CLEAR ALL LEVELS
# ==============================

async def clear_levels(guild_id: int):

    config = await get_guild_config(guild_id)

    config["levels"] = []

    await save_guild_config(guild_id, config)
