# Danh sách prompt có sẵn.
# key KHÔNG được đổi sau khi đã có user trả lời (nó là khóa để query).
# Muốn sửa chữ -> đổi `text`, giữ nguyên `key`.

PROMPTS = [
    {"key": "cook_worst", "text": "Món tôi nấu dở nhất là..."},
    {"key": "weekend", "text": "Cuối tuần lý tưởng của tôi là..."},
    {"key": "irrational", "text": "Nỗi sợ vô lý nhất của tôi..."},
    {"key": "rant", "text": "Chủ đề tôi có thể nói liên tục 2 tiếng..."},
    {"key": "green_flag", "text": "Green flag tôi để ý đầu tiên ở người khác..."},
    {"key": "3am", "text": "3 giờ sáng bạn sẽ thấy tôi đang..."},
    {"key": "convince", "text": "Cho tôi 30 giây để thuyết phục bạn rằng..."},
    {"key": "guilty", "text": "Sở thích tôi hơi ngại thừa nhận..."},
    {"key": "last_search", "text": "Thứ gần nhất tôi google lúc 2h sáng..."},
    {"key": "game", "text": "Game/phim/nhạc tôi sẽ bắt bạn thử cho bằng được..."},
    {"key": "unpopular", "text": "Quan điểm không được lòng ai của tôi..."},
    {"key": "perfect_date", "text": "Buổi hẹn đầu hoàn hảo với tôi là..."},
]

BY_KEY = {p["key"]: p for p in PROMPTS}

def get_prompt(key: str) -> dict:
    return BY_KEY.get(key)

def is_valid_prompt_key(key: str) -> bool:
    return key in BY_KEY

# Số prompt user phải trả lời để profile được coi là hoàn chỉnh.
REQUIRED_PROMPTS = 2

# Tối đa hiển thị trên card (nhiều quá rối mắt).
MAX_PROMPTS = 3
