import json
import os
import threading

DATA_FILE = "data/embeds.json"

# single process lock only (NOT async, but safe minimal)
lock = threading.RLock()


# =========================
# INTERNAL
# =========================

def load_all():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}


def save_all(data):
    os.makedirs("data", exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    # ONLY lock write section (fix double-lock issue)
    with lock:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        os.replace(temp_file, DATA_FILE)


# =========================
# PUBLIC API
# =========================

def save_embed(guild_id, name=None, data=None):

    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    guild_id = str(guild_id)

    with lock:
        all_data = load_all()

        if guild_id not in all_data:
            all_data[guild_id] = {}

        all_data[guild_id][name] = data

        save_all(all_data)


def load_embed(guild_id, name=None):

    if name is None:
        return None

    all_data = load_all()

    return all_data.get(str(guild_id), {}).get(name)


def delete_embed(guild_id, name=None):

    if name is None:
        return False

    guild_id = str(guild_id)

    with lock:
        all_data = load_all()

        if guild_id in all_data and name in all_data[guild_id]:

            del all_data[guild_id][name]

            if not all_data[guild_id]:
                del all_data[guild_id]

            save_all(all_data)
            return True

    return False


def get_all_embeds(guild_id):

    all_data = load_all()

    return all_data.get(str(guild_id), {})


def get_all_embed_names(guild_id=None):

    if guild_id is None:
        return []

    all_data = load_all()

    return list(all_data.get(str(guild_id), {}).keys())
