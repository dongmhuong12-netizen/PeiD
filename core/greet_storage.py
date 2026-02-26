import json
import os

FILE_PATH = "data/greet_leave.json"


def _load_all():
    if not os.path.exists(FILE_PATH):
        return {}

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_all(data: dict):
    os.makedirs("data", exist_ok=True)

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_guild_config(guild_id: int):
    data = _load_all()
    return data.get(str(guild_id), {})


def update_guild_config(guild_id: int, section: str, key: str, value):
    """
    section: "greet" hoặc "leave"
    key: "channel" | "embed" | "message"
    """
    data = _load_all()

    guild_id = str(guild_id)

    if guild_id not in data:
        data[guild_id] = {
            "greet": {},
            "leave": {}
        }

    if section not in data[guild_id]:
        data[guild_id][section] = {}

    data[guild_id][section][key] = value

    _save_all(data)


def get_section(guild_id: int, section: str):
    config = get_guild_config(guild_id)
    return config.get(section, {})
