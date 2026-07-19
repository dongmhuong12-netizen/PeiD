# Mã hóa/giải mã customId của component.
# Discord giới hạn customId 100 ký tự. Format: `d|<kind>|<args...>`

P = "d"
SEP = "|"

def j(*parts: str) -> str:
    """Nối chuỗi ID và kiểm tra giới hạn 100 ký tự"""
    custom_id = SEP.join([P] + [str(p) for p in parts])
    if len(custom_id) > 100:
        raise ValueError(f"customId quá dài ({len(custom_id)}/100): {custom_id}")
    return custom_id

class ID:
    """Bộ tạo Custom ID chuẩn xác cho các nút bấm và modal"""
    @staticmethod
    def swipe(action: str, target_id: str): return j("sw", action, target_id)
    
    @staticmethod
    def swipe_next(): return j("nx")
    
    @staticmethod
    def report_open(target_id: str): return j("ro", target_id)
    
    @staticmethod
    def report_submit(target_id: str): return j("rs", target_id)
    
    @staticmethod
    def block(target_id: str): return j("bl", target_id)
    
    @staticmethod
    def profile_setup(): return j("ps")
    
    @staticmethod
    def profile_modal(section: str): return j("pm", section) # 'basics' hoặc 'prompts'
    
    @staticmethod
    def profile_prefs(): return j("pp")
    
    @staticmethod
    def profile_socials(): return j("so")
    
    @staticmethod
    def profile_tags(): return j("pt")
    
    @staticmethod
    def profile_tags_select(): return j("ts")
    
    @staticmethod
    def profile_socials_modal(platform: str): return j("sm", platform)
    
    @staticmethod
    def match_ready(match_id: str): return j("mr", match_id)
    
    @staticmethod
    def match_decline(match_id: str): return j("md", match_id)
    
    @staticmethod
    def unmatch_ask(match_id: str): return j("ua", match_id)
    
    @staticmethod
    def unmatch_do(match_id: str): return j("ud", match_id)
    
    @staticmethod
    def superlike_note(target_id: str): return j("sn", target_id)
    
    @staticmethod
    def cupid_perms(target_id: str): return j("cp", target_id)
    
    @staticmethod
    def quiz_start(match_id: str): return j("qst", match_id)
    
    @staticmethod
    def quiz_ans(opt_idx: int): return j("qan", str(opt_idx))
    
    @staticmethod
    def destiny_like(user_id: str): return j("dsl", user_id)
    
    @staticmethod
    def noop(): return j("no")

def parse_id(custom_id: str) -> dict:
    """Giải mã Custom ID thành dạng Dictionary để bot xử lý"""
    if not custom_id or not custom_id.startswith(P + SEP):
        return None
        
    parts = custom_id.split(SEP)
    # Cấu trúc an toàn: [prefix, kind, a, b, c]
    kind = parts[1] if len(parts) > 1 else None
    a = parts[2] if len(parts) > 2 else None
    b = parts[3] if len(parts) > 3 else None
    
    if kind == "sw": return {"kind": "swipe", "action": a, "targetId": b}
    if kind == "nx": return {"kind": "swipe_next"}
    if kind == "ro" and a: return {"kind": "report_open", "targetId": a}
    if kind == "rs" and a: return {"kind": "report_submit", "targetId": a}
    if kind == "bl" and a: return {"kind": "block", "targetId": a}
    if kind == "ps": return {"kind": "profile_setup"}
    if kind == "pm" and a in ["basics", "prompts"]: return {"kind": "profile_modal", "section": a}
    if kind == "pp": return {"kind": "profile_prefs"}
    if kind == "so": return {"kind": "profile_socials"}
    if kind == "pt": return {"kind": "profile_tags"}
    if kind == "ts": return {"kind": "profile_tags_select"}
    if kind == "sm" and a: return {"kind": "profile_socials_modal", "platform": a}
    if kind == "mr" and a: return {"kind": "match_ready", "matchId": a}
    if kind == "md" and a: return {"kind": "match_decline", "matchId": a}
    if kind == "ua" and a: return {"kind": "unmatch_ask", "matchId": a}
    if kind == "ud" and a: return {"kind": "unmatch_do", "matchId": a}
    if kind == "sn" and a: return {"kind": "superlike_note", "targetId": a}
    if kind == "cp" and a: return {"kind": "cupid_perms", "targetId": a}
    if kind == "qst" and a: return {"kind": "quiz_start", "matchId": a}
    if kind == "dsl" and a: return {"kind": "destiny_like", "userId": a}
    if kind == "no": return {"kind": "noop"}
    
    return None
