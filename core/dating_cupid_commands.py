# Metadata quyền — dữ liệu thuần, làm nguồn sự thật duy nhất (Single Source of Truth)

ALL_PERMISSIONS = [
    "GIVE_SUPERLIKE",
    "REVIEW_REPORTS",
    "MODERATE_PROFILE",
    "VIEW_STATS"
]

PERMISSION_LABEL = {
    "GIVE_SUPERLIKE": "Cấp Super Like",
    "REVIEW_REPORTS": "Xử lý báo cáo",
    "MODERATE_PROFILE": "Cấm / bỏ cấm hồ sơ",
    "VIEW_STATS": "Xem số liệu",
}

PERMISSION_HINT = {
    "GIVE_SUPERLIKE": "Cấp và thu hồi Super Like cho thành viên",
    "REVIEW_REPORTS": "Đọc báo cáo, đánh dấu đã xử lý hoặc bỏ qua",
    "MODERATE_PROFILE": "Cấm hồ sơ vi phạm, bỏ cấm, bỏ ẩn",
    "VIEW_STATS": "Xem thống kê server",
}

# Ánh xạ: subcommand của /cupid -> quyền nó đòi hỏi để chạy.
# Nếu tạo lệnh mới mà quên bỏ vào đây, bot sẽ tự động ngắt lệnh.
CUPID_REQUIRED = {
    "give": "GIVE_SUPERLIKE",
    "balance": "GIVE_SUPERLIKE",
    "reports": "REVIEW_REPORTS",
    "resolve": "REVIEW_REPORTS",
    "ban": "MODERATE_PROFILE",
    "unban": "MODERATE_PROFILE",
    "status": "VIEW_STATS",
}
