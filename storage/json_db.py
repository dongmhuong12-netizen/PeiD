import json
import os
from typing import Dict, Any
from core.database import BaseDatabase


DATA_FILE = "data.json"


class JSONDatabase(BaseDatabase):
    def __init__(self):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

    # =========================
    # Internal helpers
    # =========================

    def _load(self) -> Dict[str, Any]:
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]) -> None:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def _ensure_guild(self, data: Dict[str, Any], guild_id: int):
        gid = str(guild_id)
        if gid not in data:
            data[gid] = {
                "embeds": {},
                "greet": None,
                "leave": None
            }
        return data

    # =========================
    # Guild Base Data
    # =========================

    async def get_guild(self, guild_id: int) -> Dict[str, Any]:
        data = self._load()
        data = self._ensure_guild(data, guild_id)
        return data[str(guild_id)]

    async def save_guild(self, guild_id: int, guild_data: Dict[str, Any]) -> None:
        data = self._load()
        data[str(guild_id)] = guild_data
        self._save(data)

    async def delete_guild(self, guild_id: int) -> None:
        data = self._load()
        data.pop(str(guild_id), None)
        self._save(data)

    # =========================
    # Embed System
    # =========================

    async def get_embeds(self, guild_id: int) -> Dict[str, Any]:
        guild = await self.get_guild(guild_id)
        return guild.get("embeds", {})

    async def save_embed(
        self,
        guild_id: int,
        embed_name: str,
        embed_data: Dict[str, Any]
    ) -> None:
        data = self._load()
        data = self._ensure_guild(data, guild_id)
        data[str(guild_id)]["embeds"][embed_name] = embed_data
        self._save(data)

    async def delete_embed(
        self,
        guild_id: int,
        embed_name: str
    ) -> None:
        data = self._load()
        data = self._ensure_guild(data, guild_id)
        data[str(guild_id)]["embeds"].pop(embed_name, None)
        self._save(data)

    # =========================
    # Greet / Leave
    # =========================

    async def set_greet(self, guild_id: int, greet_data: Dict[str, Any]) -> None:
        data = self._load()
        data = self._ensure_guild(data, guild_id)
        data[str(guild_id)]["greet"] = greet_data
        self._save(data)

    async def get_greet(self, guild_id: int) -> Dict[str, Any] | None:
        guild = await self.get_guild(guild_id)
        return guild.get("greet")

    async def set_leave(self, guild_id: int, leave_data: Dict[str, Any]) -> None:
        data = self._load()
        data = self._ensure_guild(data, guild_id)
        data[str(guild_id)]["leave"] = leave_data
        self._save(data)

    async def get_leave(self, guild_id: int) -> Dict[str, Any] | None:
        guild = await self.get_guild(guild_id)
        return guild.get("leave")
