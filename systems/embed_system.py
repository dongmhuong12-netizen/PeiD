import re
import discord
from core.embed_storage import save_embed, load_embed, get_all_embeds
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

class EmbedSystem:
    # Hạn mức 50 Embed mỗi server
    LIMIT = 50

    @staticmethod
    async def create_embed(guild_id: int, name: str):
        """
        quy trình khởi tạo embed mới.
        bảo tồn 100% logic validation và async flow.
        """
        # 1. VALIDATION (Giữ nguyên Regex)
        if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            # TRẢ VỀ TEXT THUẦN
            return False, "tên embed không hợp lệ. chỉ chấp nhận chữ cái, số, khoảng trắng và dấu `-` hoặc `_` thôi nhé"

        clean_name = name.strip()

        # 2. EXISTS CHECK (Giữ nguyên Await)
        if await load_embed(guild_id, clean_name):
            # TRẢ VỀ EMBED (Sẽ được handle ở command layer hoặc bọc ngay tại đây nếu cậu muốn)
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree... tên embed này đã tồn tại rồi. cậu hãy chọn một cái tên khác nhé",
                color=0xf8bbd0
            )
            return False, embed_err

        # 3. ENFORCE LIMIT (Giữ nguyên Await)
        all_embeds = await get_all_embeds(guild_id)
        if len(all_embeds) >= EmbedSystem.LIMIT:
            embed_limit = discord.Embed(
                description=f"{Emojis.HOICHAM} hmm..? server của cậu đã đạt giới hạn {EmbedSystem.LIMIT} embed rồi. hãy xoá bớt trước khi tạo mới nhé",
                color=0xf8bbd0
            )
            return False, embed_limit

        # 4. CREATE DEFAULT (Giữ nguyên 100% Schema, chỉ cập nhật màu thương hiệu)
        default_data = {
            "title": "tiêu đề embed mới",
            "description": "nội dung mô tả mặc định",
            "color": 0xf8bbd0, # Cập nhật màu hồng hệ thống
            "image": None,
            "thumbnail": None,
            "author": {"name": None, "icon_url": None, "url": None},
            "footer": {"text": None, "icon_url": None},
            "fields": [] 
        }

        # 5. SAVE
        await save_embed(guild_id, clean_name, default_data)
        print(f"[system] created new embed '{clean_name}' for guild {guild_id}", flush=True)

        return True, None
