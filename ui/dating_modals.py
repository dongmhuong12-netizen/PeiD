import discord
from core.dating_prompts import PROMPTS, REQUIRED_PROMPTS
from core.dating_report_reasons import REPORT_REASONS
from core.dating_socials import social_spec

# Giả lập biến từ theme.ts và limits.ts (Sẽ link lại sau khi sếp gửi)
GENDER_LABEL = {
    "MALE": "Nam", "FEMALE": "Nữ", 
    "NONBINARY": "Phi nhị giới", "OTHER": "Khác"
}
LIMITS = {"promptAnswerMaxLength": 300, "bioMaxLength": 500, "superLikeNoteMaxLength": 100}

def clamp_desc(s: str) -> str:
    """Cắt cứng chuỗi không vượt quá 100 ký tự (Tránh lỗi API Discord)"""
    return s[:99] + "…" if len(s) > 100 else s

# ==========================================
# 1. MODAL: THÔNG TIN CƠ BẢN & ẢNH
# ==========================================
class BasicsModal(discord.ui.Modal):
    def __init__(self, existing: dict = None):
        super().__init__(
            title="Sửa thông tin" if existing else "Tạo hồ sơ",
            custom_id="profile_modal_basics"
        )
        
        self.add_item(discord.ui.TextInput(
            custom_id="name",
            label="Tên hiển thị",
            style=discord.TextStyle.short,
            min_length=2, max_length=32,
            required=True,
            placeholder="Tên bạn muốn người khác gọi",
            default=existing.get("displayName") if existing else None
        ))

        self.add_item(discord.ui.TextInput(
            custom_id="age",
            label="Tuổi (Bot chỉ dành cho 18+)",
            style=discord.TextStyle.short,
            min_length=2, max_length=2,
            required=True,
            placeholder="18",
            default=str(existing.get("age")) if existing else None
        ))

        self.add_item(discord.ui.Select(
            custom_id="gender",
            placeholder="Giới tính của bạn",
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(
                    label=GENDER_LABEL.get(g, g), value=g, 
                    default=(existing and existing.get("gender") == g)
                ) for g in ["MALE", "FEMALE", "NONBINARY", "OTHER"]
            ]
        ))

        self.add_item(discord.ui.Select(
            custom_id="seeking",
            placeholder="Bạn muốn tìm (Chọn nhiều)",
            min_values=1, max_values=4,
            options=[
                discord.SelectOption(
                    label=GENDER_LABEL.get(g, g), value=g, 
                    default=(existing and g in existing.get("seeking", []))
                ) for g in ["MALE", "FEMALE", "NONBINARY", "OTHER"]
            ]
        ))

        photo_required = not existing.get("photoUrl") if existing else True
        
        # Nếu discord.py của sếp hỗ trợ FileInput trong Modal:
        try:
            self.add_item(discord.ui.FileInput(
                custom_id="photo", 
                required=photo_required
            ))
        except AttributeError:
            # Fallback an toàn nếu thư viện chưa update FileInput
            self.add_item(discord.ui.TextInput(
                custom_id="photoUrl",
                label="Link Ảnh (Bắt buộc)" if photo_required else "Đổi ảnh (Để trống giữ cũ)",
                style=discord.TextStyle.short,
                required=photo_required,
                placeholder="Dán link ảnh Discord vào đây"
            ))

# ==========================================
# 2. MODAL: CÂU HỎI THẢ THÍNH & BIO
# ==========================================
class PromptsModal(discord.ui.Modal):
    def __init__(self, existing: dict = None):
        super().__init__(title="Câu trả lời của bạn", custom_id="profile_modal_prompts")
        
        answers = existing.get("prompts", []) if existing else []
        answers.sort(key=lambda x: x.get("position", 0))

        # Yêu cầu 2 câu hỏi (REQUIRED_PROMPTS = 2) -> Tốn 4 slot (2 Select, 2 Text)
        for i in range(REQUIRED_PROMPTS):
            cur = answers[i] if i < len(answers) else None
            
            self.add_item(discord.ui.Select(
                custom_id=f"prompt{i}",
                placeholder=f"Chọn câu hỏi {i + 1}",
                min_values=1, max_values=1,
                options=[
                    discord.SelectOption(
                        label=p["text"][:97] + "..." if len(p["text"]) > 100 else p["text"],
                        value=p["key"],
                        default=(cur and cur.get("promptKey") == p["key"])
                    ) for p in PROMPTS
                ]
            ))

            self.add_item(discord.ui.TextInput(
                custom_id=f"answer{i}",
                label=f"Trả lời {i + 1}",
                style=discord.TextStyle.paragraph,
                min_length=2, max_length=LIMITS["promptAnswerMaxLength"],
                required=True,
                default=cur.get("answer") if cur else None
            ))

        # Slot thứ 5 (Cuối cùng): Bio tự do
        self.add_item(discord.ui.TextInput(
            custom_id="bio",
            label="Giới thiệu ngắn (Không bắt buộc)",
            style=discord.TextStyle.paragraph,
            max_length=LIMITS["bioMaxLength"],
            required=False,
            default=existing.get("bio") if existing else None
        ))

# ==========================================
# 3. MODAL: BỘ LỌC TÌM KIẾM
# ==========================================
class PrefsModal(discord.ui.Modal):
    def __init__(self, existing: dict):
        super().__init__(title="Bộ lọc tìm kiếm", custom_id="profile_prefs")
        
        self.add_item(discord.ui.Select(
            custom_id="seeking",
            placeholder="Bạn muốn tìm",
            min_values=1, max_values=4,
            options=[
                discord.SelectOption(
                    label=GENDER_LABEL.get(g, g), value=g, 
                    default=(g in existing.get("seeking", []))
                ) for g in ["MALE", "FEMALE", "NONBINARY", "OTHER"]
            ]
        ))

        self.add_item(discord.ui.TextInput(
            custom_id="min",
            label="Tuổi tối thiểu (Không nhỏ hơn 18)",
            style=discord.TextStyle.short,
            max_length=2, required=True,
            default=str(existing.get("seekAgeMin", 18))
        ))

        self.add_item(discord.ui.TextInput(
            custom_id="max",
            label="Tuổi tối đa",
            style=discord.TextStyle.short,
            max_length=2, required=True,
            default=str(existing.get("seekAgeMax", 99))
        ))

# ==========================================
# 4. MODAL: MẠNG XÃ HỘI
# ==========================================
class SocialModal(discord.ui.Modal):
    def __init__(self, platform: str, current: str = None):
        spec = social_spec(platform)
        super().__init__(
            title=spec["label"] if spec else "Link", 
            custom_id=f"profile_socials_{platform}"
        )
        
        hint = spec["hint"] if spec else ""
        self.add_item(discord.ui.TextInput(
            custom_id="value",
            label="Tài khoản",
            style=discord.TextStyle.short,
            max_length=200, required=False,
            placeholder=clamp_desc(f"{hint} · Để trống = gỡ link"),
            default=current
        ))

# ==========================================
# 5. MODAL: GỬI LỜI NHẮN SUPER LIKE
# ==========================================
class SuperLikeNoteModal(discord.ui.Modal):
    def __init__(self, target_id: str, name: str):
        super().__init__(title="Super Like", custom_id=f"superlike_note_{target_id}")
        
        self.add_item(discord.ui.TextInput(
            custom_id="note",
            label=f"Nhắn gì đó cho {name}",
            style=discord.TextStyle.paragraph,
            max_length=LIMITS["superLikeNoteMaxLength"],
            required=False,
            placeholder="Không bắt buộc — để trống cũng được."
        ))

# ==========================================
# 6. MODAL: TỐ CÁO (REPORT)
# ==========================================
class ReportModal(discord.ui.Modal):
    def __init__(self, target_id: str, name: str):
        super().__init__(title=f"Báo cáo {name}"[:45], custom_id=f"report_submit_{target_id}")
        
        self.add_item(discord.ui.Select(
            custom_id="reason",
            placeholder="Chọn lý do",
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(label=r["label"], value=r["key"]) 
                for r in REPORT_REASONS
            ]
        ))

        self.add_item(discord.ui.TextInput(
            custom_id="details",
            label="Chi tiết (Không bắt buộc)",
            style=discord.TextStyle.paragraph,
            max_length=500, required=False,
            placeholder="Giúp mod xử lý nhanh hơn."
        ))
