import json
import os

DATA_FILE = "storage/embeds.json"


class EmbedStorage:

    @staticmethod
    def _ensure():
        os.makedirs("storage", exist_ok=True)
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

    @staticmethod
    def load():
        EmbedStorage._ensure()
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save(data: dict):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def get_guild(guild_id: int):
        data = EmbedStorage.load()
        return data.get(str(guild_id), {})

    @staticmethod
    def create(guild_id: int, name: str):
        data = EmbedStorage.load()
        gid = str(guild_id)

        if gid not in data:
            data[gid] = {}

        data[gid][name] = {
            "title": None,
            "description": None,
            "color": "0x2f3136",
            "image_url": None,
            "thumbnail_url": None,
            "footer": None,
            "author": None,
            "fields": []
        }

        EmbedStorage.save(data)
