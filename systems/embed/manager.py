import json
import os
import discord
from typing import Optional

DATA_FILE = "storage/embeds.json"


class EmbedManager:
    def __init__(self):
        os.makedirs("storage", exist_ok=True)
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

    def _load(self):
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    async def create_embed(
        self,
        embed_id: str,
        title: str,
        description: str,
        color: int = 0x2F3136,
        image_url: Optional[str] = None,
    ):
        data = self._load()

        data[embed_id] = {
            "title": title,
            "description": description,
            "color": color,
            "image_url": image_url,
        }

        self._save(data)

    async def update_embed(self, embed_id: str, **kwargs):
        data = self._load()

        if embed_id not in data:
            return False

        for key, value in kwargs.items():
            if value is not None:
                data[embed_id][key] = value

        self._save(data)
        return True

    async def delete_embed(self, embed_id: str):
        data = self._load()

        if embed_id not in data:
            return False

        del data[embed_id]
        self._save(data)
        return True

    async def get_embed(self, embed_id: str) -> Optional[discord.Embed]:
        data = self._load()

        if embed_id not in data:
            return None

        embed_data = data[embed_id]

        embed = discord.Embed(
            title=embed_data["title"],
            description=embed_data["description"],
            color=embed_data["color"],
        )

        if embed_data.get("image_url"):
            embed.set_image(url=embed_data["image_url"])

        return embed
