import re
import discord
import asyncio
from collections import defaultdict
from core.embed_storage import save_embed, load_embed, get_all_embeds
# [VÁ LỖI] Import mạch ghi đĩa vĩnh viễn để bot không bao giờ quên
from core.cache_manager import save as force_save
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# [VÁ LỖI] Lock theo Guild để tránh Race Condition khi nhiều người tạo cùng lúc
_guild_locks = defaultdict(asyncio.Lock)

class EmbedSystem:
    # Hạn mức 50 Embed mỗi server (IT Pro: Tránh lạm dụng tài nguyên RAM)
    LIMIT = 50

    @staticmethod
    async def create_embed(guild_id: int, name: str):
        """
        quy trình khởi tạo embed mới.
        bảo tồn 100% logic validation và async flow.
        """
        
        # [VÁ LỖI] Sử dụng Lock để đảm bảo quy trình Check-then-Save là duy nhất (Atomic)
        lock = _guild_locks[guild_id]
        async with lock:
            try:
                # 1. VALIDATION (Giữ nguyên Regex chuẩn của sếp)
                if not name or not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
                    # TRẢ VỀ TEXT THUẦN ĐỂ COMMAND XỬ LÝ
                    return False, "tên embed không hợp lệ. chỉ chấp nhận chữ cái, số, khoảng trắng và dấu `-` hoặc `_` thôi nhé"

                # [GIA CỐ] Chuẩn hóa tên đồng nhất với Storage (lowercase) để không bao giờ lạc mất nhau
                clean_name = name.strip().lower()

                # 2. EXISTS CHECK (IT Pro: Chống ghi đè dữ liệu cũ)
                if await load_embed(guild_id, clean_name):
                    # TRẢ VỀ EMBED LỖI ĐỂ HIỂN THỊ TRỰC QUAN
                    embed_err = discord.Embed(
                        description=f"{Emojis.HOICHAM} aree... tên embed này đã tồn tại rồi. cậu hãy chọn một cái tên khác nhé",
                        color=0xf8bbd0
                    )
                    return False, embed_err

                # 3. ENFORCE LIMIT (IT Pro: Kiểm soát quy mô database)
                all_embeds = await get_all_embeds(guild_id)
                if len(all_embeds) >= EmbedSystem.LIMIT:
                    embed_limit = discord.Embed(
                        description=f"{Emojis.HOICHAM} hmm..? server của cậu đã đạt giới hạn {EmbedSystem.LIMIT} embed rồi. hãy xoá bớt trước khi tạo mới nhé",
                        color=0xf8bbd0
                    )
                    return False, embed_limit

                # 4. CREATE DEFAULT (CẬP NHẬT SCHEMA PHASE 3)
                # IT Pro: Mọi Embed mới đều được cấp sẵn mạch "buttons" để tránh lỗi KeyError khi cấy 9 hệ thống.
                default_data = {
                    "title": "tiêu đề embed mới",
                    "description": "nội dung mô tả mặc định",
                    "color": 0xf8bbd0, # Màu hồng thương hiệu của Yiyi
                    "image": None,
                    "thumbnail": None,
                    "author": {"name": None, "icon_url": None, "url": None},
                    "footer": {"text": None, "icon_url": None},
                    "fields": [],
                    "buttons": [] # [THÊM MỚI] Ngăn chứa cho 9 hệ thống: Verify, Gacha, Ticket, Vote, v.v.
                }

                # 5. SAVE (Đồng bộ vào Storage Atomic)
                await save_embed(guild_id, clean_name, default_data)
                
                # [CỰC QUAN TRỌNG] Chốt hạ ghi đĩa ngay lập tức để bot không bao giờ quên
                await force_save("embeds")
                
                print(f"[system] created new embed '{clean_name}' for guild {guild_id} and forced cache sync", flush=True)

                return True, None
            finally:
                # [VÁ LỖI] Dọn dẹp RAM: Xóa Lock khỏi bộ nhớ sau khi xử lý xong để tránh Memory Leak
                if guild_id in _guild_locks and not lock.locked():
                    _guild_locks.pop(guild_id, None)


