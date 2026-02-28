import json
import os

DATA_FILE = "data/embeds.json"


def load_all():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_all(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# PUBLIC API
# =========================

def save_embed(guild_id: int, name: str, data: dict):
    all_data = load_all()

    guild_id = str(guild_id)

    if guild_id not in all_data:
        all_data[guild_id] = {}

    all_data[guild_id][name] = data
    save_all(all_data)


def load_embed(guild_id: int, name: str):
    all_data = load_all()
    return all_data.get(str(guild_id), {}).get(name)


def delete_embed(guild_id: int, name: str):
    all_data = load_all()
    guild_id = str(guild_id)

    if guild_id in all_data and name in all_data[guild_id]:
        del all_data[guild_id][name]
        save_all(all_data)
        return True

    return False


def get_all_embeds(guild_id: int):
    all_data = load_all()
    return all_data.get(str(guild_id), {})
