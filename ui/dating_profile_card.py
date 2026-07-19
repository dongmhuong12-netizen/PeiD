import discord
from typing import List, Dict, Any, Tuple, Optional

from core.dating_prompts import get_prompt, MAX_PROMPTS
from core.dating_socials import social_display
from core.dating_tags import get_tag

# Giả lập Theme & Glyphs (Sẽ khớp với file theme.ts sếp gửi sau)
COLOR = {
    "slate": 0x64748B, "rose": 0xF43F5E, 
    "violet": 0x8B5CF6, "gold": 0xF59E0B, "crimson": 0xDC2626
}
GLYPH = {"dot": "•", "like": "💚", "pass": "❌", "superLike": "⭐", "report": "🚩", "sparkle": "✨", "edit": "✏️"}
PLATFORM_GLYPH = {"INSTAGRAM": "📸", "FACEBOOK": "📘", "TIKTOK": "🎵", "SPOTIFY": "🎧", "TWITTER": "🐦"}
PLATFORM_LABEL = {"INSTAGRAM": "Instagram", "FACEBOOK": "Facebook", "TIKTOK": "TikTok", "SPOTIFY": "Spotify", "TWITTER": "X (Twitter)"}
GENDER_LABEL = {"MALE": "Nam", "FEMALE": "Nữ", "NONBINARY": "Phi nhị giới", "OTHER": "Khác"}

def get_glyph(glyphs: Optional[Dict[str, str]], key: str) -> str:
    if glyphs and key in glyphs:
        return glyphs[key]
    return GLYPH.get(key, "❓")

def tags_list(p: Dict[str, Any]) -> Optional[str]:
    tags = p.get("tags", [])
    if not tags:
        return None
    
    formatted_tags = []
    for t in tags:
        spec = get_tag(t)
        if spec:
            formatted_tags.append(f"`{spec['emoji']} {spec['label']}`")
        else:
            formatted_tags.append(f"`{t}`")
    return "  ".join(formatted_tags)

def build_header_desc(p: Dict[str, Any], show_activity: bool = False) -> str:
    """Tạo đoạn Header Text chứa Tên, Tuổi, Giới tính"""
    name = p.get("displayName", "Unknown")
    age = p.get("age", "?")
    gender_raw = p.get("gender", "OTHER")
    gender = GENDER_LABEL.get(gender_raw, gender_raw)
    
    out = f"### {name} {GLYPH['dot']} {age}\n"
    meta_line = f"*{gender}*"
    # Note: Tạm bỏ qua hàm timeAgo chi tiết, có thể thay bằng chuỗi "hoạt động gần đây"
    if show_activity:
        meta_line += f" {GLYPH['dot']} *hoạt động gần đây*"
    
    out += f"{meta_line}\n"
    return out

def build_prompts_desc(p: Dict[str, Any]) -> str:
    """Ghép các câu hỏi thả thính thành đoạn văn bản"""
    prompts = p.get("prompts", [])
    if not prompts:
        return ""
    
    prompts_sorted = sorted(prompts, key=lambda x: x.get("position", 0))[:MAX_PROMPTS]
    blocks = []
    for pa in prompts_sorted:
        q = get_prompt(pa.get("promptKey"))
        if q:
            blocks.append(f"**{q['text']}**\n{pa.get('answer')}")
        else:
            blocks.append(pa.get("answer"))
    
    return "\n\n".join(blocks)

# =========================================================================
# CARD KHI ĐANG LƯỚT QUẸT
# =========================================================================
def swipe_card(
    p: Dict[str, Any], 
    avatar_url: Optional[str], 
    ctx: Dict[str, Any]
) -> Tuple[discord.Embed, discord.ui.View]:
    """Tạo Embed và View cho việc lướt Tinder"""
    incoming = ctx.get("incomingSuperLike")
    you_super_liked = ctx.get("youSuperLiked", False)
    glyphs = ctx.get("glyphs")
    
    embed = discord.Embed(color=COLOR["violet"] if incoming else COLOR["rose"])
    
    # 📌 Xử lý hiển thị Avatar User ở góc phải phía trên Embed (Thumbnail)
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    desc = ""
    # Banner Super Like
    if incoming:
        desc += f"### {get_glyph(glyphs, 'superLike')} {p.get('displayName')} đã Super Like bạn\n"
        note = incoming.get("note")
        if note:
            safe_note = note.replace('\n', '\n> ')
            desc += f"> {safe_note}\n\n"
        desc += "──────────────\n\n"

    desc += build_header_desc(p, show_activity=True) + "\n"

    tags = tags_list(p)
    if tags:
        desc += f"{tags}\n\n"

    bio = p.get("bio")
    if bio:
        safe_bio = bio.replace('\n', '\n> ')
        desc += f"> {safe_bio}\n\n"

    blocks = build_prompts_desc(p)
    if blocks:
        desc += "──────────────\n\n"
        desc += blocks + "\n\n"

    embed.description = desc
    
    if p.get("photoUrl"):
        embed.set_image(url=p["photoUrl"])

    # Xây dựng Nút bấm (View)
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        custom_id=f"swipe_like_{p['userId']}", label="Thích", 
        emoji=get_glyph(glyphs, "like"), style=discord.ButtonStyle.success
    ))
    view.add_item(discord.ui.Button(
        custom_id=f"swipe_pass_{p['userId']}", label="Bỏ qua", 
        emoji=get_glyph(glyphs, "pass"), style=discord.ButtonStyle.secondary
    ))
    
    super_btn = discord.ui.Button(
        custom_id=f"swipe_super_{p['userId']}", label="Super Like", 
        emoji=get_glyph(glyphs, "superLike"), style=discord.ButtonStyle.primary
    )
    if you_super_liked or ctx.get("superLikes", 0) <= 0:
        super_btn.disabled = True
    view.add_item(super_btn)
    
    view.add_item(discord.ui.Button(
        custom_id=f"report_open_{p['userId']}", label="Báo cáo", 
        emoji=get_glyph(glyphs, "report"), style=discord.ButtonStyle.secondary
    ))

    # Footer thông tin lượt quẹt
    footer_text = ""
    if you_super_liked:
        footer_text += f"{get_glyph(glyphs, 'superLike')} Đã Super Like — giờ Thích hoặc Bỏ qua • "
    footer_text += f"Còn {ctx.get('swipesLeft', 0)} lượt hôm nay"
    if ctx.get("superLikes", 0) > 0:
        footer_text += f" • {ctx.get('superLikes')} super like"
    
    embed.set_footer(text=footer_text)

    return embed, view

# =========================================================================
# CARD XEM PROFILE CỦA CHÍNH MÌNH
# =========================================================================
def self_card(
    p: Dict[str, Any], 
    avatar_url: Optional[str], 
    missing: List[str], 
    glyphs: Optional[Dict[str, str]] = None
) -> Tuple[discord.Embed, discord.ui.View]:
    ready = len(missing) == 0
    embed = discord.Embed(color=COLOR["rose"] if ready else COLOR["slate"])
    
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    desc = build_header_desc(p, show_activity=False) + "\n"
    
    tags = tags_list(p)
    if tags:
        desc += f"{tags}\n\n"
        
    bio = p.get("bio")
    if bio:
        desc += f"> {bio.replace(chr(10), chr(10)+'> ')}\n\n"

    blocks = build_prompts_desc(p)
    if blocks:
        desc += "──────────────\n\n" + blocks + "\n\n"

    socials = p.get("socials", [])
    if socials:
        desc += "──────────────\n\n"
        soc_list = []
        for s in socials:
            plt = s.get("platform")
            val = s.get("value")
            icon = PLATFORM_GLYPH.get(plt, "🔗")
            soc_list.append(f"{icon} {social_display(plt, val)}")
        desc += "   ".join(soc_list) + "\n*Chỉ hiện với người đã match với bạn.*\n\n"

    if not ready:
        desc += "──────────────\n\n"
        desc += "**Chưa xong**\n" + "\n".join([f"• {m}" for m in missing]) + "\n"
        desc += "*Profile chưa xuất hiện với ai cho đến khi hoàn tất.*\n"

    embed.description = desc
    if p.get("photoUrl"):
        embed.set_image(url=p["photoUrl"])

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(custom_id="profile_modal_basics", label="Sửa thông tin", emoji=get_glyph(glyphs, "edit"), style=discord.ButtonStyle.secondary))
    view.add_item(discord.ui.Button(custom_id="profile_modal_prompts", label="Sửa câu trả lời", style=discord.ButtonStyle.secondary))
    view.add_item(discord.ui.Button(custom_id="profile_prefs", label="Bộ lọc", style=discord.ButtonStyle.secondary))
    view.add_item(discord.ui.Button(custom_id="profile_socials", label="Link MXH", style=discord.ButtonStyle.secondary))
    
    return embed, view

# =========================================================================
# CARD KHI MATCH NHAU (LỘ LINK MXH)
# =========================================================================
def match_reveal_card(
    p: Dict[str, Any], 
    avatar_url: Optional[str], 
    match_id: str, 
    glyphs: Optional[Dict[str, str]] = None
) -> Tuple[discord.Embed, discord.ui.View]:
    embed = discord.Embed(color=COLOR["gold"])
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    desc = build_header_desc(p, show_activity=True) + "\n"
    
    tags = tags_list(p)
    if tags:
        desc += f"{tags}\n\n"
        
    blocks = build_prompts_desc(p)
    if blocks:
        desc += "──────────────\n\n" + blocks + "\n\n"

    desc += "──────────────\n\n"
    socials = p.get("socials", [])
    if socials:
        desc += f"**{get_glyph(glyphs, 'sparkle')} Link của {p.get('displayName')}**\n"
        for s in socials:
            plt = s.get("platform")
            icon = PLATFORM_GLYPH.get(plt, "🔗")
            label = PLATFORM_LABEL.get(plt, plt)
            desc += f"{icon} {label} — {social_display(plt, s.get('value'))}\n"
    else:
        desc += f"*{p.get('displayName')} chưa gắn link MXH nào.*\n"

    embed.description = desc
    if p.get("photoUrl"):
        embed.set_image(url=p["photoUrl"])

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(custom_id=f"unmatch_ask_{match_id}", label="Hủy match", style=discord.ButtonStyle.danger))
    view.add_item(discord.ui.Button(custom_id=f"report_open_{p['userId']}", label="Báo cáo", emoji=get_glyph(glyphs, "report"), style=discord.ButtonStyle.secondary))

    return embed, view

# =========================================================================
# CARD THÔNG BÁO CHUNG
# =========================================================================
def notice(title: str, body: str = None, footer: str = None, color: int = COLOR["slate"]) -> discord.Embed:
    embed = discord.Embed(title=title, color=color)
    if body:
        embed.description = body
    if footer:
        embed.set_footer(text=footer)
    return embed

# =========================================================================
# QUẺ BÓI DUYÊN PHẬN HÀNG NGÀY
# =========================================================================
def destiny_card(
    p: Dict[str, Any], 
    avatar_url: Optional[str], 
    shared_tags: List[str]
) -> Tuple[discord.Embed, discord.ui.View]:
    embed = discord.Embed(color=COLOR["gold"])
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    desc = "### ✨ QUẺ BÓI DUYÊN PHẬN HÀNG NGÀY ✨\n\n"
    
    if not shared_tags:
        desc += "🌌 *\"Đi tìm nét đối lập. Sự khác biệt cá tính giữa hai bạn chính là miếng ghép hoàn hảo để bù trừ cho nhau.\"*\n\n"
    elif len(shared_tags) <= 2:
        desc += f"🌱 *\"Nhịp đập chung nho nhỏ. Hai bạn chia sẻ sở thích chung là **{', '.join(shared_tags)}**. Một buổi cafe trò chuyện nhẹ nhàng sẽ khởi đầu duyên nợ!\"*\n\n"
    else:
        desc += f"🔥 *\"Định mệnh vẫy gọi! Hai bạn có sự tương hợp tuyệt vời với {len(shared_tags)} tags chung: **{', '.join(shared_tags)}**. Thích ngay kẻo bỏ lỡ cơ duyên tốt!\"*\n\n"

    desc += "──────────────\n\n"
    desc += build_header_desc(p, show_activity=False) + "\n"
    
    tags = tags_list(p)
    if tags:
        desc += f"{tags}\n\n"

    bio = p.get("bio")
    if bio:
        desc += f"> {bio.replace(chr(10), chr(10)+'> ')}\n\n"

    blocks = build_prompts_desc(p)
    if blocks:
        desc += "──────────────\n\n" + blocks + "\n\n"

    embed.description = desc
    if p.get("photoUrl"):
        embed.set_image(url=p["photoUrl"])

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        custom_id=f"destiny_like_{p['userId']}", 
        label="Thích Duyên Phận 💖", 
        style=discord.ButtonStyle.success
    ))

    return embed, view
