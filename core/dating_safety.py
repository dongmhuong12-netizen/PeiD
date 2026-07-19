import datetime
import discord
from core.dating_storage import db, get_profile, get_guild_config, block_user, check_block
from core.dating_report_reasons import get_reason

# Collections
reports_col = db.reports
blocks_col = db.blocks
profiles_col = db.profiles

# Giới hạn số lượng Report 1 người có thể gửi trong 24h để chống phá hoại
REPORTS_PER_DAY_LIMIT = 5

async def file_report(
    client: discord.Client,
    guild_id: str,
    reporter_id: str,
    reported_id: str,
    reason_key: str,
    details: str = None
) -> dict:
    """Nộp 1 đơn tố cáo vi phạm"""
    reason = get_reason(reason_key)
    if not reason:
        return {"kind": "no_profile"}

    target = await get_profile(guild_id, reported_id)
    if not target:
        return {"kind": "no_profile"}

    # 1. Kiểm tra giới hạn 24h (Chống 1 người spam report liên tục nhiều người)
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    recent_count = await reports_col.count_documents({
        "guildId": str(guild_id),
        "reporterId": str(reporter_id),
        "createdAt": {"$gte": since}
    })
    
    if recent_count >= REPORTS_PER_DAY_LIMIT:
        return {"kind": "rate_limited", "perDay": REPORTS_PER_DAY_LIMIT}

    # 2. Chụp Snapshot (Lưu lại chứng cứ vi phạm ngay tại thời điểm report)
    snapshot = {
        "displayName": target.get("displayName"),
        "age": target.get("age"),
        "gender": target.get("gender"),
        "bio": target.get("bio"),
        "photoUrl": target.get("photoUrl"),
        "prompts": target.get("prompts", []),
        "socials": target.get("socials", []),
        "capturedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    # 3. Tạo Report (Dùng _id ghép để chống 1 người tố 1 người nhiều lần)
    report_id = f"{guild_id}_{reporter_id}_{reported_id}"
    
    existing = await reports_col.find_one({"_id": report_id})
    if existing:
        return {"kind": "already_reported"}

    await reports_col.insert_one({
        "_id": report_id,
        "guildId": str(guild_id),
        "reporterId": str(reporter_id),
        "reportedId": str(reported_id),
        "reason": reason["key"],
        "details": details[:500] if details else None, # Giới hạn chữ 
        "snapshot": snapshot,
        "status": "OPEN",
        "createdAt": datetime.datetime.now(datetime.timezone.utc)
    })

    # 4. Auto-Block 2 chiều giữa người tố và bị tố
    await block_user(reporter_id, reported_id)

    # Đếm xem có bao nhiêu người khác cũng đang tố cáo mục tiêu này
    open_count = await reports_col.count_documents({
        "guildId": str(guild_id),
        "reportedId": str(reported_id),
        "status": "OPEN"
    })

    # 5. Gửi cảnh báo đỏ cho Mod
    await notify_mods(
        client=client,
        guild_id=guild_id,
        reporter_id=reporter_id,
        reported_id=reported_id,
        reason=reason,
        details=details,
        open_count=open_count,
        snapshot=snapshot
    )

    return {"kind": "filed"}

async def notify_mods(
    client: discord.Client,
    guild_id: str,
    reporter_id: str,
    reported_id: str,
    reason: dict,
    details: str,
    open_count: int,
    snapshot: dict
):
    """Báo động về Kênh Mod (Nếu có cài đặt)"""
    cfg = await get_guild_config(guild_id)
    if not cfg or not cfg.get("modChannelId"):
        return

    try:
        channel = await client.fetch_channel(int(cfg["modChannelId"]))
    except Exception:
        return

    if not isinstance(channel, discord.TextChannel):
        return

    is_urgent = reason.get("severe", False)
    
    # Thiết kế Embed Cảnh Báo
    embed = discord.Embed(
        title="🚨 KHẨN — Nghi hồ sơ dưới tuổi" if is_urgent else "⚑ Report Mới",
        color=discord.Color.red() if is_urgent else discord.Color.dark_gray()
    )
    
    desc = f"**Bị báo cáo:** <@{reported_id}> — {snapshot.get('displayName', 'Unknown')}, Tuổi: {snapshot.get('age', '?')}\n"
    desc += f"**Người báo:** <@{reporter_id}>\n"
    desc += f"**Lý do:** {reason.get('label')}\n"
    if details:
        desc += f"**Chi tiết:** {details}\n"
    desc += f"**Số report đang mở:** {open_count}"
    
    embed.description = desc
    
    if snapshot.get("photoUrl"):
        embed.set_thumbnail(url=snapshot["photoUrl"])
        embed.add_field(name="Link Ảnh Gốc", value=f"[Nhấn vào đây]({snapshot['photoUrl']})")
        
    footer_text = "Ưu tiên xem ngay! Nếu vi phạm, dùng /cupid ban để khóa." if is_urgent else "Hồ sơ KHÔNG bị khóa tự động. Xử lý: /cupid reports hoặc /cupid ban"
    embed.set_footer(text=footer_text)

    await channel.send(embed=embed)
