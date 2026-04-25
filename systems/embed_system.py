import re
from core.embed_storage import save_embed, load_embed, get_all_embeds

class EmbedSystem:
    # Hạn mức 50 Embed mỗi server - Chuẩn tối ưu cho server quy mô lớn
    LIMIT = 50

    @staticmethod
    def create_embed(guild_id: int, name: str):
        """
        Quy trình khởi tạo Embed mới:
        Validation -> Check Trùng -> Check Hạn mức -> Khởi tạo Schema.
        """
        # 1. VALIDATION (GIỮ NGUYÊN LOGIC NGUYỆT)
        # Cho phép: Chữ, số, khoảng trắng, gạch dưới, gạch ngang.
        if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            return False, "INVALID_NAME"

        # Dọn dẹp khoảng trắng để tránh lỗi ID trùng lặp do cách gõ
        clean_name = name.strip()

        # 2. EXISTS CHECK: Đảm bảo không ghi đè Embed đang có
        if load_embed(guild_id, clean_name):
            return False, "EXISTS"

        # 3. ENFORCE LIMIT: Bảo vệ tài nguyên hệ thống
        all_embeds = get_all_embeds(guild_id)
        if len(all_embeds) >= EmbedSystem.LIMIT:
            return False, "LIMIT_REACHED"

        # 4. CREATE DEFAULT (ĐỒNG BỘ SCHEMA):
        # Thiết lập Schema đầy đủ để EmbedUIView không bị KeyError
        default_data = {
            "title": "Tiêu đề Embed mới",
            "description": "Nội dung mô tả mặc định.",
            "color": 0x5865F2, # Blurple chuẩn Discord
            "image": None,
            "thumbnail": None,
            "author": {"name": None, "icon_url": None, "url": None},
            "footer": {"text": None, "icon_url": None},
            "fields": [] # Khởi tạo list rỗng cho các mốc nâng cao
        }

        # Lưu xuống Storage
        save_embed(guild_id, clean_name, default_data)
        print(f"[SYSTEM] Created new embed '{clean_name}' for Guild {guild_id}", flush=True)

        return True, None
