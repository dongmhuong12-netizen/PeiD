import json
import os
import asyncio
import tempfile
import shutil

DATA_FILE = "data/booster_levels.json"

_lock = asyncio.Lock()


# ==============================
# ENSURE FILE EXISTS
# ==============================

def _ensure_file():

    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):

        with open(DATA_FILE, "w", encoding="utf8") as f:
            json.dump({}, f)


# ==============================
# LOAD DATA SAFE
# ==============================

def _load():

    _ensure_file()

    try:

        with open(DATA_FILE, "r", encoding="utf8") as f:
            return json.load(f)

    except json.JSONDecodeError:

        # file bị hỏng → reset
        return {}


# ==============================
# ATOMIC SAVE (ANTI DATA LOSS)
# ==============================

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
# GET GUILD CONFIG
# ==============================

async def get_guild_config(guild_id: int):

    async with _lock:

        data = _load()

        return data.get(str(guild_id), {
            "booster_role": None,
            "channel": None,
            "levels": {}
        })


# ==============================
# SAVE CONFIG
# ==============================

async def save_guild_config(guild_id: int, config: dict):

    async with _lock:

        data = _load()

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
# SET LEVEL
# ==============================

async def set_level(guild_id: int, level: int, role_id: int, days: int):

    config = await get_guild_config(guild_id)

    config["levels"][str(level)] = {
        "role": role_id,
        "days": days
    }

    await save_guild_config(guild_id, config)


# ==============================
# CLEAR LEVEL
# ==============================

async def clear_level(guild_id: int, level: int):

    config = await get_guild_config(guild_id)

    if str(level) in config["levels"]:

        del config["levels"][str(level)]

    await save_guild_config(guild_id, config)


# ==============================
# GET LEVELS
# ==============================

async def get_levels(guild_id: int):

    config = await get_guild_config(guild_id)

    return config["levels"]
