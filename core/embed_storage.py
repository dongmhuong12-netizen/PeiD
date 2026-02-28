import json
import os

DATA_FILE = "data/embeds.json"


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
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# PUBLIC API
# =========================

# SAVE
def save_embed(guild_id, name=None, data=None):
    # Cho phép kiểu cũ: save_embed(name, data)
    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    all_data = load_all()
    guild_id = str(guild_id)

    if guild_id not in all_data:
        all_data[guild_id] = {}

    all_data[guild_id][name] = data
    save_all(all_data)


# LOAD
def load_embed(guild_id, name=None):
    all_data = load_all()

    # Nếu gọi kiểu cũ load_embed(name)
    if name is None:
        name = guild_id
        # Tìm embed này trong mọi guild
        for g in all_data:
            if name in all_data[g]:
                return all_data[g][name]
        return None

    return all_data.get(str(guild_id), {}).get(name)


# DELETE
def delete_embed(guild_id, name=None):
    all_data = load_all()

    # Kiểu cũ delete_embed(name)
    if name is None:
        name = guild_id
        for g in list(all_data.keys()):
            if name in all_data[g]:
                del all_data[g][name]
                if not all_data[g]:
                    del all_data[g]
                save_all(all_data)
                return True
        return False

    guild_id = str(guild_id)

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
    all_data = load_all()

    # Kiểu cũ: không truyền guild
    if guild_id is None:
        names = []
        for g in all_data:
            names.extend(all_data[g].keys())
        return names

    return list(all_data.get(str(guild_id), {}).keys())
