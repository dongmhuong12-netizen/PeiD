from storage.embed_storage import EmbedStorage


class EmbedSystem:

    LIMIT = 15

    @staticmethod
    def create_embed(guild_id: int, name: str):

        if not name.isalnum():
            return False, "INVALID_NAME"

        guild_data = EmbedStorage.get_guild(guild_id)

        if name in guild_data:
            return False, "EXISTS"

        if len(guild_data) >= EmbedSystem.LIMIT:
            return False, "LIMIT"

        guild_data[name] = {
            "title": None,
            "description": None,
            "color": "2F3136",
            "image": None
        }

        return True, None
