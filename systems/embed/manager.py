from typing import Dict, Any


class EmbedManager:
    MAX_EMBEDS = 10

    def __init__(self, db):
        self.db = db

    async def create_embed(self, guild_id: int, name: str) -> Dict[str, Any]:
        embeds = await self.db.get_embeds(guild_id)

        if name in embeds:
            raise ValueError("Tồn tại một embed tương tự, không thể tạo.")

        if len(embeds) >= self.MAX_EMBEDS:
            raise ValueError("Vượt số lượng embed, cần xoá embed cũ để thay thế.")

        embed_data = {
            "title": "",
            "description": "",
            "color": 0x2b2d31,
            "fields": [],
            "footer": None,
            "thumbnail": None,
            "image": None
        }

        await self.db.save_embed(guild_id, name, embed_data)
        return embed_data

    async def get_embed(self, guild_id: int, name: str) -> Dict[str, Any] | None:
        embeds = await self.db.get_embeds(guild_id)
        return embeds.get(name)

    async def delete_embed(self, guild_id: int, name: str):
        embeds = await self.db.get_embeds(guild_id)

        if name not in embeds:
            raise ValueError("Embed không tồn tại.")

        await self.db.delete_embed(guild_id, name)

    async def update_embed(
        self,
        guild_id: int,
        name: str,
        new_data: Dict[str, Any]
    ):
        embeds = await self.db.get_embeds(guild_id)

        if name not in embeds:
            raise ValueError("Embed không tồn tại.")

        await self.db.save_embed(guild_id, name, new_data)
