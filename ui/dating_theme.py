import time
from datetime import datetime

# ==========================================
# 1. BẢNG MÀU (Hex Colors)
# ==========================================
COLOR = {
    "rose": 0xe0576b,     # Profile card. Hồng đất, ấm.
    "gold": 0xe8a33d,     # Khoảnh khắc match (Phần thưởng)
    "mint": 0x4ec9a0,     # Xác nhận, thành công
    "slate": 0x8b95a5,    # Thông tin trung tính, trạng thái rỗng
    "crimson": 0xd94040,  # Cảnh báo, report, unmatch
    "violet": 0x8b7cf6,   # Super like
}

# ==========================================
# 2. GLYPHS & EMOJI (Bắt buộc là Unicode Emoji thật)
# ==========================================
GLYPH = {
    "like": "💗",
    "pass": "❌",
    "superLike": "⭐",
    "report": "🚩",
    "chat": "💬",
    "edit": "📝",
    "photo": "🖼",
    "sparkle": "✨",
    "dot": "·",
}

PLATFORM_GLYPH = {
    "INSTAGRAM": "📷",
    "FACEBOOK": "🌐",
    "TIKTOK": "🎵",
    "SPOTIFY": "🎧",
    "TWITTER": "𝕏",
    "OTHER": "🔗",
}

# ==========================================
# 3. TỪ ĐIỂN HIỂN THỊ (Labels)
# ==========================================
GENDER_LABEL = {
    "MALE": "Nam",
    "FEMALE": "Nữ",
    "NONBINARY": "Phi nhị nguyên",
    "OTHER": "Khác",
}

PLATFORM_LABEL = {
    "INSTAGRAM": "Instagram",
    "FACEBOOK": "Facebook",
    "TIKTOK": "TikTok",
    "SPOTIFY": "Spotify",
    "TWITTER": "X",
    "OTHER": "Khác",
}

# ==========================================
# 4. HÀM TIỆN ÍCH ĐỊNH DẠNG (Formatters)
# ==========================================
def sub(s: str) -> str:
    """Cú pháp subtext của Discord: chữ nhỏ, màu mờ."""
    return f"-# {s}"

def meta(*parts) -> str:
    """Ngăn cách các mục metadata trên 1 dòng: Nữ · 23 · Hoạt động 2h trước"""
    valid_parts = [str(p) for p in parts if p]
    return f"  {GLYPH['dot']}  ".join(valid_parts)

def time_ago(date_input) -> str:
    """Đổi thời gian sang định dạng tương đối Tiếng Việt (Kiểm soát độ chính xác tốt hơn <t:unix:R>)"""
    if not date_input:
        return "không rõ"
        
    if isinstance(date_input, datetime):
        timestamp = date_input.timestamp()
    else:
        timestamp = float(date_input)
        
    s = max(0, int(time.time() - timestamp))
    
    if s < 120: return "vừa xong"
    m = s // 60
    if m < 60: return f"{m} phút trước"
    h = m // 60
    if h < 24: return f"{h} giờ trước"
    d = h // 24
    if d == 1: return "hôm qua"
    if d < 7: return f"{d} ngày trước"
    w = d // 7
    if w < 5: return f"{w} tuần trước"
    return "lâu rồi"

