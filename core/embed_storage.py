import json
import os

FILE_PATH = "data/embeds.json"


def _load_all():
    if not os.path.exists(FILE_PATH):
        return {}

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def save_embed(name: str, embed_data: dict):
    data = _load_all()
    data[name] = embed_data
    _save_all(data)


def load_embed(name: str):
    data = _load_all()
    return data.get(name)


def delete_embed(name: str):
    data = _load_all()
    if name in data:
        del data[name]
        _save_all(data)
        return True
    return False


def list_embeds():
    return list(_load_all().keys())
