from core.embed_storage import save_embed, load_embed, get_all_embeds


class EmbedSystem:

    LIMIT = 15

    @staticmethod
    def create_embed(guild_id: int, name: str):

        # =========================
        # VALIDATION
        # =========================
        if not name or not name.isalnum():
            return False, "INVALID_NAME"

        # =========================
        # EXISTS CHECK
        # =========================
        if load_embed(guild_id, name):
            return False, "EXISTS"

        # =========================
        # ENFORCE LIMIT PER GUILD
        # =========================
        all_embeds = get_all_embeds(guild_id)

        if len(all_embeds) >= EmbedSystem.LIMIT:
            return False, "LIMIT_REACHED"

        # =========================
        # CREATE DEFAULT EMBED
        # =========================
        save_embed(guild_id, name, {
            "title": None,
            "description": None,
            "color": 0x2F3136,
            "image": None
        })

        return True, None
