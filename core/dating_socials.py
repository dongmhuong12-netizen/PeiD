import re
from urllib.parse import urlparse

# Danh sách các nền tảng và bộ quy tắc kiểm tra khắt khe để chống Phishing/Scam
SPECS = [
    {
        "platform": "INSTAGRAM",
        "label": "Instagram",
        "handle": re.compile(r"^[a-zA-Z0-9._]{1,30}$"),
        "hosts": ["instagram.com", "www.instagram.com"],
        "url": lambda h: f"https://instagram.com/{h}",
        "hint": "vidu: linh.nguyen hoặc instagram.com/linh.nguyen",
    },
    {
        "platform": "FACEBOOK",
        "label": "Facebook",
        "handle": re.compile(r"^[a-zA-Z0-9._-]{5,50}$"),
        "hosts": ["facebook.com", "www.facebook.com", "fb.com", "m.facebook.com"],
        "url": lambda h: f"https://facebook.com/{h}",
        "hint": "vidu: linh.nguyen.9 hoặc facebook.com/linh.nguyen.9",
    },
    {
        "platform": "TIKTOK",
        "label": "TikTok",
        "handle": re.compile(r"^[a-zA-Z0-9._]{2,24}$"),
        "hosts": ["tiktok.com", "www.tiktok.com"],
        "url": lambda h: f"https://tiktok.com/@{h}",
        "hint": "vidu: linhcooks hoặc tiktok.com/@linhcooks",
    },
    {
        "platform": "SPOTIFY",
        "label": "Spotify",
        "handle": re.compile(r"^[a-zA-Z0-9]{1,64}$"),
        "hosts": ["open.spotify.com", "spotify.com"],
        "url": lambda h: f"https://open.spotify.com/user/{h}",
        "hint": "dán link profile Spotify của bạn",
    },
    {
        "platform": "TWITTER",
        "label": "X (Twitter)",
        "handle": re.compile(r"^[a-zA-Z0-9_]{1,15}$"),
        "hosts": ["x.com", "twitter.com", "www.x.com", "www.twitter.com"],
        "url": lambda h: f"https://x.com/{h}",
        "hint": "vidu: linhng hoặc x.com/linhng",
    },
]

BY_PLATFORM = {s["platform"]: s for s in SPECS}

def social_specs() -> list:
    return SPECS

def social_spec(platform: str) -> dict:
    return BY_PLATFORM.get(platform)

def parse_social(platform: str, raw: str) -> dict:
    """
    Bóc tách handle ra từ bất kỳ thứ gì user dán vào, rồi validate.
    Chỉ chấp nhận các handle hợp lệ hoặc link thuộc đúng domain an toàn.
    """
    spec = BY_PLATFORM.get(platform)
    if not spec:
        return {"ok": False, "error": "Nền tảng không hợp lệ."}

    s = raw.strip()
    if not s:
        return {"ok": False, "error": "Bạn chưa nhập gì."}

    # Kiểm tra nếu người dùng dán cả 1 đường link URL
    if re.match(r"^https?://", s, re.IGNORECASE) or re.match(r"^[\w.-]+\.[a-z]{2,}/", s, re.IGNORECASE):
        with_proto = s if re.match(r"^https?://", s, re.IGNORECASE) else f"https://{s}"
        
        try:
            u = urlparse(with_proto)
        except Exception:
            return {"ok": False, "error": "Link không hợp lệ."}

        host = u.hostname.lower() if u.hostname else ""
        if host not in spec["hosts"]:
            return {
                "ok": False,
                "error": f"Link phải thuộc {spec['hosts'][0]}. Hoặc chỉ cần nhập tên tài khoản."
            }

        # Bóc tách đường dẫn
        seg = [x for x in u.path.split("/") if x]
        if not seg:
            return {"ok": False, "error": "Không tìm thấy tên tài khoản trong link."}

        candidate = None
        if spec["platform"] == "SPOTIFY":
            candidate = seg[1] if len(seg) > 1 and seg[0] == "user" else None
        else:
            candidate = seg[0]

        if not candidate:
            return {"ok": False, "error": "Không tìm thấy tên tài khoản trong link."}
        
        s = candidate

    # Dọn dẹp ký tự @ ở đầu nếu có
    s = re.sub(r"^@", "", s).strip()

    if not spec["handle"].match(s):
        return {"ok": False, "error": f"Tên tài khoản không hợp lệ. {spec['hint']}"}

    return {"ok": True, "handle": s}

def social_url(platform: str, handle: str) -> str:
    """Dựng URL an toàn để hiển thị"""
    spec = BY_PLATFORM.get(platform)
    return spec["url"](handle) if spec else None

def social_display(platform: str, handle: str) -> str:
    """Định dạng chuỗi Markdown để hiển thị trên Embed Discord"""
    url = social_url(platform, handle)
    shown = "profile" if platform == "SPOTIFY" else f"@{handle}"
    return f"[{shown}]({url})" if url else shown
