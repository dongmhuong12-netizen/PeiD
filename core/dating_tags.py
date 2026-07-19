# Danh sách các Tag sở thích có sẵn (Tương tự Prompts, key lưu trong Database)

TAGS = [
    {"key": "game", "label": "Chơi Game", "emoji": "🎮"},
    {"key": "music", "label": "Nghe Nhạc", "emoji": "🎵"},
    {"key": "anime", "label": "Anime / Manga", "emoji": "🎎"},
    {"key": "movie", "label": "Xem Phim", "emoji": "🎬"},
    {"key": "travel", "label": "Du Lịch", "emoji": "✈️"},
    {"key": "food", "label": "Ẩm Thực", "emoji": "🍕"},
    {"key": "sports", "label": "Thể Thao", "emoji": "⚽"},
    {"key": "photo", "label": "Nhiếp Ảnh", "emoji": "📸"},
    {"key": "reading", "label": "Đọc Sách", "emoji": "📚"},
    {"key": "coding", "label": "Lập Trình", "emoji": "💻"},
    {"key": "cafe", "label": "Đi Cafe", "emoji": "☕"},
    {"key": "gym", "label": "Tập Gym / Fitness", "emoji": "💪"},
    {"key": "pet", "label": "Thú Cưng", "emoji": "🐱"},
    {"key": "fashion", "label": "Thời Trang", "emoji": "👗"},
    {"key": "art", "label": "Vẽ / Nghệ Thuật", "emoji": "🎨"},
]

BY_KEY = {t["key"]: t for t in TAGS}

def get_tag(key: str) -> dict:
    return BY_KEY.get(key)

def is_valid_tag(key: str) -> bool:
    return key in BY_KEY

# Giới hạn số lượng tag tối đa một Profile được chọn
MAX_TAGS = 8
