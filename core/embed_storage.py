import json
import os
import threading

DATA_FILE = "data/embeds.json"

# lock chống ghi đè khi nhiều lệnh chạy cùng lúc
lock = threading.Lock()


# =========================
# INTERNAL
# =========================

def load_all():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}


def save_all(data):
    os.makedirs("data", exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    # ghi file tạm trước
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    # replace atomically
    os.replace(temp_file, DATA_FILE)


# =========================
# PUBLIC API
# =========================

# SAVE
def save_embed(guild_id, name=None, data=None):

    # hỗ trợ kiểu cũ
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


# LOAD
def load_embed(guild_id, name=None):

    if name is None:
        return None

    all_data = load_all()

    return all_data.get(str(guild_id), {}).get(name)


# DELETE
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
