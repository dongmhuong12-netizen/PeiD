import re
from core.embed_storage import save_embed, load_embed, get_all_embeds

class EmbedSystem:
    # Hạn mức 50 Embed mỗi server
    LIMIT = 50

    @staticmethod
    async def create_embed(guild_id: int, name: str): # CHUYỂN SANG ASYNC
        """
        Quy trình khởi tạo Embed mới (Bản sửa lỗi treo máy do lệch pha Async).
        """
        # 1. VALIDATION
        if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            return False, "INVALID_NAME"

        clean_name = name.strip()

        # 2. EXISTS CHECK: Phải dùng await vì storage xử lý I/O async
        if await load_embed(guild_id, clean_name):
            return False, "EXISTS"

        # 3. ENFORCE LIMIT: Phải dùng await
        all_embeds = await get_all_embeds(guild_id)
        if len(all_embeds) >= EmbedSystem.LIMIT:
            return False, "LIMIT_REACHED"

        # 4. CREATE DEFAULT (Giữ nguyên 100% Schema của Nguyệt)
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

        # 5. SAVE: Bắt buộc await để ghi xong mới nhả Interaction
        await save_embed(guild_id, clean_name, default_data)
        print(f"[SYSTEM] Created new embed '{clean_name}' for Guild {guild_id}", flush=True)

        return True, None
