# Danh sách câu hỏi trắc nghiệm để phá vỡ bầu không khí ngượng ngùng lúc mở Thread

QUIZ_QUESTIONS = [
    {
        "text": "Buổi hẹn hò đầu tiên lý tưởng của bạn sẽ là?",
        "options": [
            "Quán cafe yên tĩnh, nhẹ nhàng chill chill ☕",
            "Đi phượt, leo núi trải nghiệm thiên nhiên ngoại ô ⛰️",
            "Net cỏ chiến game, leo rank thâu đêm 🎮",
            "Rạp chiếu phim xem phim bom tấn 🎬"
        ]
    },
    {
        "text": "Nếu đối phương bất ngờ biến mất không rep tin nhắn suốt 2 ngày?",
        "options": [
            "Lo lắng hỏi han xem họ có gặp chuyện gì không 🥺",
            "Hơi dỗi một tí, họ nhắn lại thì tỏ thái độ 😤",
            "Kệ họ, mình vẫn tiếp tục cuộc sống bình thường 🍃",
            "Tự động ngầm hiểu là 'hết duyên' và block luôn 🚫"
        ]
    },
    {
        "text": "Hình mẫu người yêu lý tưởng của bạn thiên về gì?",
        "options": [
            "Ngoại hình cuốn hút, nhìn là yêu ngay 😍",
            "Tâm hồn đồng điệu, nói chuyện hợp gu ✨",
            "Tính cách ấm áp, biết quan tâm chăm sóc 🌻",
            "Tài năng vượt trội, có chí tiến thủ lớn 🚀"
        ]
    },
    {
        "text": "Khi có mâu thuẫn hay cãi cọ, bạn sẽ làm gì?",
        "options": [
            "Im lặng suy nghĩ, khi bình tĩnh mới nói chuyện 🤐",
            "Phải nói rõ ràng ngay lập tức cho ra nhẽ 🗣️",
            "Nhờ bạn bè, người thân vào làm trung gian hoà giải 👥",
            "Chủ động nhận lỗi trước để giữ hoà khí dù mình đúng hay sai 🙏"
        ]
    },
    {
        "text": "Bạn thích đi du lịch kiểu nào nhất?",
        "options": [
            "Resort sang chảnh nghỉ dưỡng thảnh thơi 🏖️",
            "Du lịch bụi khám phá các vùng đất mới 🎒",
            "Du lịch tâm linh, đi chùa cầu may 🏛️",
            "Chỉ muốn ở nhà nằm ngủ hưởng thụ ngày nghỉ 🛌"
        ]
    }
]

# Hàm buildQuestionCard ở bản gốc (dùng notice, ButtonBuilder) 
# sẽ được Yiyi xử lý ở khâu vẽ UI Discord sau (file cogs). 
# Ở đây ta chỉ cần xuất bộ dữ liệu câu hỏi ra ngoài là đủ.
def get_quiz_question(index: int) -> dict:
    if 0 <= index < len(QUIZ_QUESTIONS):
        return QUIZ_QUESTIONS[index]
    return None
