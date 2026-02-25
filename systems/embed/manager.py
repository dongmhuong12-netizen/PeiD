from typing import Dict, Any


class EmbedManager:
    def __init__(self, db):
        self.db = db

    # =========================
    # CREATE / SAVE
    # =========================
    async def save_embed(
        self,
        guild_id: int,
        name: str,
        embed_data: Dict[str, Any],
        embed_type: str = "custom",  # "custom" hoặc "system"
    ) -> Dict[str, Any]:

        embeds = await self.db.get_embeds(guild_id)

        # Thêm type nếu chưa có
        embed_data["type"] = embed_type

        embeds[name] = embed_data
        await self.db.save_embed(guild_id, name, embed_data)

        return embed_data

    # =========================
    # READ
    # =========================
    async def get_embed(self, guild_id: int, name: str):
        embeds = await self.db.get_embeds(guild_id)
        return embeds.get(name)

    async def get_all_embeds(self, guild_id: int):
        return await self.db.get_embeds(guild_id)

    # =========================
    # UPDATE
    # =========================
    async def update_embed(
        self,
        guild_id: int,
        name: str,
        new_data: Dict[str, Any],
    ) -> Dict[str, Any]:

        embeds = await self.db.get_embeds(guild_id)

        if name not in embeds:
            raise ValueError("Embed không tồn tại.")

        current = embeds[name]

        # Không cho sửa type
        embed_type = current.get("type", "custom")

        # Merge dữ liệu
        current.update(new_data)
        current["type"] = embed_type

        await self.db.save_embed(guild_id, name, current)

        return current

    # =========================
    # DELETE
    # =========================
    async def delete_embed(self, guild_id: int, name: str):

        embeds = await self.db.get_embeds(guild_id)

        if name not in embeds:
            raise ValueError("Embed không tồn tại.")

        if embeds[name].get("type") == "system":
            raise ValueError("Không thể xoá embed hệ thống.")

        await self.db.delete_embed(guild_id, name)

        return True
