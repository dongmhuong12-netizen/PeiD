import typing
from core.dating_storage import db

# Trỏ đến collection lưu override glyphs
glyphs_col = db.guild_glyphs

# Bảng Emoji mặc định (Sẽ chạy nếu Server không cài Emoji tùy chỉnh)
DEFAULT_GLYPHS = {
    "like": "💚",
    "pass": "❌",
    "superLike": "⭐",
    "report": "🚩",
    "chat": "💬",
    "edit": "✏️",
    "photo": "📸",
    "sparkle": "✨",
    "dot": "•"  # Dot là ký tự text thuần, không cho phép đổi
}

# Cấu hình hiển thị thông tin cho Admin khi dùng lệnh cài đặt
CUSTOMIZABLE_GLYPHS = {
    "like": {"label": "Thích", "description": "Nút quẹt Thích khi lướt hồ sơ"},
    "pass": {"label": "Bỏ qua", "description": "Nút quẹt Bỏ qua khi lướt hồ sơ"},
    "superLike": {"label": "Super Like", "description": "Biểu tượng Super Like"},
    "report": {"label": "Báo cáo", "description": "Nút báo cáo hồ sơ vi phạm"},
    "chat": {"label": "Chat", "description": "Nút Bắt đầu chat / Vào Chat"},
    "edit": {"label": "Chỉnh sửa", "description": "Nút chỉnh sửa hồ sơ"},
    "photo": {"label": "Ảnh", "description": "Nhãn ảnh hồ sơ"},
    "sparkle": {"label": "Nổi bật", "description": "Biểu tượng Match / tỏa sáng"},
}

# Khởi tạo Cache trên RAM (Tránh spam query Database)
# Cấu trúc: { "guild_id": { "key": "emoji_string" } }
_glyph_cache: typing.Dict[str, typing.Dict[str, str]] = {}


async def get_glyph_config(guild_id: str) -> typing.Dict[str, str]:
    """Lấy tất cả glyph override cho 1 guild, dùng cache."""
    guild_id = str(guild_id)
    
    # Nếu đã lưu trong RAM thì bốc ra luôn, không chọc DB nữa
    if guild_id in _glyph_cache:
        return _glyph_cache[guild_id]

    # Nếu chưa có, query DB và nạp vào RAM
    rows = glyphs_col.find({"guildId": guild_id})
    config_map = {}
    async for row in rows:
        config_map[row["key"]] = row["value"]

    _glyph_cache[guild_id] = config_map
    return config_map


def get_glyph_sync(config_map: typing.Dict[str, str], key: str) -> str:
    """Lấy giá trị đồng bộ sau khi đã có cache, nếu không có thì lấy mặc định."""
    return config_map.get(key, DEFAULT_GLYPHS.get(key, "❓"))


async def get_glyph(guild_id: str, key: str) -> str:
    """Hàm tiện ích gộp 2 bước: lấy cache và lấy key (dùng nhiều nhất trong bot)."""
    config_map = await get_glyph_config(guild_id)
    return get_glyph_sync(config_map, key)


async def set_glyph(guild_id: str, key: str, value: str):
    """Lưu 1 glyph override cho guild, cập nhật vào cả DB và Cache."""
    guild_id = str(guild_id)
    
    # 1. Update DB (dùng ID ghép để chống trùng)
    await glyphs_col.update_one(
        {"_id": f"{guild_id}_{key}"},
        {"$set": {
            "guildId": guild_id,
            "key": key,
            "value": value
        }},
        upsert=True
    )

    # 2. Update RAM Cache
    if guild_id not in _glyph_cache:
        _glyph_cache[guild_id] = {}
    _glyph_cache[guild_id][key] = value


async def reset_glyph(guild_id: str, key: str):
    """Reset 1 glyph về mặc định bằng cách xóa khỏi DB và Cache."""
    guild_id = str(guild_id)
    
    await glyphs_col.delete_one({"_id": f"{guild_id}_{key}"})

    if guild_id in _glyph_cache and key in _glyph_cache[guild_id]:
        del _glyph_cache[guild_id][key]


def invalidate_glyph_cache(guild_id: str):
    """Xóa trắng cache của 1 Server để ép bot tải lại từ DB ở lần tiếp theo."""
    guild_id = str(guild_id)
    if guild_id in _glyph_cache:
        del _glyph_cache[guild_id]

