import re
from core.embed_storage import save_embed, load_embed, get_all_embeds

class EmbedSystem:
    # Nâng giới hạn để phù hợp với server quy mô lớn (100k+ members)
    LIMIT = 50

    @staticmethod
    def create_embed(guild_id: int, name: str):
        # 1. VALIDATION: Cho phép chữ, số, dấu cách và gạch ngang
        # Điều này giúp Admin đặt tên như "luat server" hay "wellcome_msg" thoải mái
        if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            return False, "INVALID_NAME"

        name = name.strip() # Dọn dẹp khoảng trắng thừa

        # 2. EXISTS CHECK: Kiểm tra trùng lặp
        if load_embed(guild_id, name):
            return False, "EXISTS"

        # 3. ENFORCE LIMIT: Kiểm tra hạn mức lưu trữ của Guild
        all_embeds = get_all_embeds(guild_id)
        if len(all_embeds) >= EmbedSystem.LIMIT:
            return False, "LIMIT_REACHED"

        # 4. CREATE DEFAULT: Khởi tạo schema chuẩn khớp với EmbedUIView
        save_embed(guild_id, name, {
            "title": "New Embed Title",
            "description": "Dùng lệnh `/p embed create` để chỉnh sửa nội dung này.",
            "color": 0x5865F2, # Màu Blurple hiện đại
            "image": None,
            "fields": [], # Sẵn sàng cho các tính năng nâng cao sau này
            "footer": {"text": None, "icon_url": None}
        })

        return True, None
