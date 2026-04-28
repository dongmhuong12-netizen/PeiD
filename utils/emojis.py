class Emojis:
    """
    Hệ thống Emoji tập trung cho Peid Bot.
    Chuẩn hóa cho quy mô 100k+ Server.
    """

    # --- NHÓM CUSTOM (CẬU CUNG CẤP) ---
    HOICHAM  = "<:emoji_50:1498482166949216276>"
    MATTRANG = "<:emoji_44:1494618535870333019>"
    YIYITIM  = "<:emoji_49:1495407155971625021>"

    # --- HÀM TIỆN ÍCH HỆ THỐNG ---
    @classmethod
    def get(cls, name: str, fallback: str = "✨"):
        """
        Lấy emoji an toàn. Nếu gõ sai tên, trả về ✨ thay vì lỗi code.
        Cách dùng: Emojis.get("HOICHAM")
        """
        return getattr(cls, name.upper(), fallback)
