from core.embed_storage import save_embed, load_embed


class EmbedSystem:

    LIMIT = 15

    @staticmethod
    def create_embed(guild_id: int, name: str):

        if not name.isalnum():
            return False, "INVALID_NAME"

        if load_embed(name):
            return False, "EXISTS"

        # Optional: nếu muốn giới hạn 15 embed thì phải đếm từ JSON
        # Hiện tại bạn chưa có get_all per guild nên bỏ LIMIT hoặc tự bổ sung

        save_embed(name, {
            "title": None,
            "description": None,
            "color": 0x2F3136,
            "image": None
        })

        return True, None
