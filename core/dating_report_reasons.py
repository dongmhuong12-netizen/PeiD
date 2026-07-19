# Danh sách lý do report — dữ liệu thuần.

REPORT_REASONS = [
    {
        "key": "minor",
        "label": "Nghi ngờ dưới 18 tuổi",
        # Cờ 'severe' dành cho các vi phạm nghiêm trọng (Vd: dưới tuổi vị thành niên).
        # Sẽ dùng cờ này để đổi màu cảnh báo đỏ chót gửi cho Mod.
        "severe": True,
    },
    {"key": "fake", "label": "Profile giả / ảnh không phải của họ"},
    {"key": "nsfw", "label": "Ảnh hoặc nội dung phản cảm"},
    {"key": "harassment", "label": "Quấy rối, xúc phạm"},
    {"key": "spam", "label": "Spam, quảng cáo, bán hàng"},
    {"key": "other", "label": "Khác"},
]

BY_KEY = {r["key"]: r for r in REPORT_REASONS}

def get_reason(key: str) -> dict:
    return BY_KEY.get(key)

def reason_label(key: str) -> str:
    reason = BY_KEY.get(key)
    return reason["label"] if reason else key
