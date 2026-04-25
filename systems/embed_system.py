import re
from core.embed_storage import save_embed, load_embed, get_all_embeds

class EmbedSystem:
    # Hạn mức 50 Embed mỗi server - Chuẩn tối ưu cho server quy mô lớn
    LIMIT = 50

    @staticmethod
    async def create_embed(guild_id: int, name: str): # Chuyển sang async để khớp với lệnh gọi await
        """
        Quy trình khởi tạo Embed mới:
        Validation -> Check Trùng -> Check Hạn mức -> Khởi tạo Schema.
        """
        # 1. VALIDATION (Giữ nguyên logic kiểm tra tên)
        if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            return False, "INVALID_NAME"

        clean_name = name.strip()

        # 2. EXISTS CHECK: Phải dùng await vì load_embed trong storage là async
        if await load_embed(guild_id, clean_name):
            return False, "EXISTS"

        # 3. ENFORCE LIMIT: Phải dùng await
        all_embeds = await get_all_embeds(guild_id)
        if len(all_embeds) >= EmbedSystem.LIMIT:
            return False, "LIMIT_REACHED"

        # 4. CREATE DEFAULT (Giữ nguyên toàn bộ Schema của Nguyệt):
        default_data = {
            "title": "Tiêu đề Embed mới",
            "description": "Nội dung mô tả mặc định.",
            "color": 0x5865F2,
            "image": None,
            "thumbnail": None,
            "author": {"name": None, "icon_url": None, "url": None},
            "footer": {"text": None, "icon_url": None},
            "fields": []
        }

        # 5. SAVE: Bắt buộc await để đảm bảo dữ liệu được ghi xong trước khi phản hồi
        await save_embed(guild_id, clean_name, default_data)
        print(f"[SYSTEM] Created new embed '{clean_name}' for Guild {guild_id}", flush=True)

        return True, None
