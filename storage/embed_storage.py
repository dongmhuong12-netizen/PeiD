class EmbedStorage:

    data = {}

    @classmethod
    def get_guild(cls, guild_id: int):
        if guild_id not in cls.data:
            cls.data[guild_id] = {}
        return cls.data[guild_id]
