import json
import os
import time

FILE_PATH = "data/voice.json"


def _load():
    if not os.path.exists(FILE_PATH):
        return {}
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    os.makedirs("data", exist_ok=True)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def set_voice(guild_id: int, channel_id: int):
    data = _load()
    data[str(guild_id)] = {
        "channel_id": channel_id,
        "enabled": True,
        "last_error": "",
        "last_update": int(time.time()),
        "last_reconnect": 0,
        "manual_leave": False
    }
    _save(data)


def remove_voice(guild_id: int):
    data = _load()
    if str(guild_id) in data:
        del data[str(guild_id)]
    _save(data)


def disable_voice(guild_id: int, reason="unknown"):
    data = _load()
    if str(guild_id) in data:
        data[str(guild_id)]["enabled"] = False
        data[str(guild_id)]["last_error"] = reason
        _save(data)


def get_voice(guild_id: int):
    data = _load()
    return data.get(str(guild_id))


def get_all():
    return _load()
