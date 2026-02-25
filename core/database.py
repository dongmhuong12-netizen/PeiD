from typing import Dict, Any


class BaseDatabase:
    """
    Abstract database layer.
    All storage systems (JSON, Mongo, SQL...) must follow this structure.
    """

    # =========================
    # Guild Base Data
    # =========================

    async def get_guild(self, guild_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    async def save_guild(self, guild_id: int, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def delete_guild(self, guild_id: int) -> None:
        raise NotImplementedError

    # =========================
    # Embed System
    # =========================

    async def get_embeds(self, guild_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    async def save_embed(
        self,
        guild_id: int,
        embed_name: str,
        embed_data: Dict[str, Any]
    ) -> None:
        raise NotImplementedError

    async def delete_embed(
        self,
        guild_id: int,
        embed_name: str
    ) -> None:
        raise NotImplementedError

    # =========================
    # Greet / Leave
    # =========================

    async def set_greet(self, guild_id: int, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def get_greet(self, guild_id: int) -> Dict[str, Any] | None:
        raise NotImplementedError

    async def set_leave(self, guild_id: int, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def get_leave(self, guild_id: int) -> Dict[str, Any] | None:
        raise NotImplementedError
