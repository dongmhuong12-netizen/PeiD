class Emojis:
    """
    Hệ thống Emoji tập trung cho Peid Bot.
    Chuẩn hóa cho quy mô 100k+ Server.
    """

    # --- NHÓM CUSTOM (CẬU CUNG CẤP) ---
    HOICHAM  = "<:emoji_50:1498482166949216276>"
    MATTRANG = "<:emoji_44:1494618535870333019>"
    WINGA    = "<:emoji_13:1504997291176759469>"
    WINGB    = "<:emoji_12:1504997233932898404>"
    HTT      = "<:emoji_21:1507801875095748690>"
    BUOMA    = "<:emoji_5:1504996011809181716>"
    BUOMB    = "<:emoji_12:1504996695425945670>"
    MOONBL   = "<:emoji_6:1504996061780119703>"
    NO       = "<:emoji_14:1504997399138140171>"
    YIYITIM  = "<:emoji_49:1495407155971625021>"

    # --- HÀM TIỆN ÍCH HỆ THỐNG ---
    @classmethod
    def get(cls, name: str, fallback: str = "✨"):
        """
        Lấy emoji an toàn. Nếu gõ sai tên, trả về ✨ thay vì lỗi code.
        Cách dùng: Emojis.get("HOICHAM")
        """
        return getattr(cls, name.upper(), fallback)
