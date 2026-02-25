import json
import os

FILE_PATH = "data/embed.json"


def save_embed(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_embed():
    if not os.path.exists(FILE_PATH):
        return None

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_embed():
    if os.path.exists(FILE_PATH):
        os.remove(FILE_PATH)
