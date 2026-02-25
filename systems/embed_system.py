import re
from storage.embed_storage import EmbedStorage

EMBED_LIMIT = 15


class EmbedSystem:

    @staticmethod
    def validate_name(name: str):
        if len(name) > 32:
            return False
        return re.match(r"^[a-zA-Z0-9_-]+$", name)

    @staticmethod
    def create_embed(guild_id: int, name: str):

        if not EmbedSystem.validate_name(name):
            return False, "INVALID_NAME"

        embeds = EmbedStorage.get_guild(guild_id)

        if name in embeds:
            return False, "EXISTS"

        if len(embeds) >= EMBED_LIMIT:
            return False, "LIMIT"

        EmbedStorage.create(guild_id, name)

        return True, None
