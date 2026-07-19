import datetime
from core.dating_storage import db, add_swipe, check_swipe, create_match, get_match

# Collections
swipes_col = db.swipes
superlikes_sent_col = db.superlikes_sent
sl_balances_col = db.sl_balances

OPT_IN_HOURS = 24  # Giới hạn lời mời chat (có thể cấu hình sau)

async def superlike_note_from(guild_id: str, from_user: str, to_user: str) -> str:
    """Kiểm tra xem người kia có gửi Super Like kèm lời nhắn cho mình không"""
    sl = await superlikes_sent_col.find_one({"_id": f"{guild_id}_{from_user}_{to_user}"})
    return sl.get("note") if sl else None

async def record_swipe(guild_id: str, from_user: str, to_user: str, action: str) -> dict:
    """
    Ghi nhận 1 lượt quẹt (LIKE/PASS) và kiểm tra Match.
    action: "LIKE" hoặc "PASS"
    """
    # 1. Ghi nhận lượt quẹt của mình trước (Dùng Upsert để đè nếu có)
    await add_swipe(guild_id, from_user, to_user, action)

    if action == "PASS":
        return {"kind": "recorded"}

    # 2. Đọc xem người kia đã quẹt mình chưa (Chỉ tìm sau khi mình đã quẹt)
    reciprocal = await check_swipe(guild_id, to_user, from_user)

    if not reciprocal or reciprocal.get("action") == "PASS":
        return {"kind": "recorded"}

    # 3. Cả 2 cùng LIKE -> Tạo Match!
    # Lấy note nếu người kia từng gửi Super Like cho mình
    their_note = await superlike_note_from(guild_id, to_user, from_user)
    
    match_id = await create_match(guild_id, from_user, to_user, opt_in_hours=OPT_IN_HOURS)
    
    # Kểm tra xem Match đã tồn tại do lỗi 2 người click quá nhanh không (Idempotent)
    existing = await get_match(match_id)
    if existing:
        return {"kind": "matched", "matchId": match_id, "theirNote": their_note}
        
    return {"kind": "matched", "matchId": match_id, "theirNote": their_note}

async def send_superlike(guild_id: str, from_user: str, to_user: str, note: str = None) -> dict:
    """Gửi vật phẩm Super Like (Chưa tính là 1 lượt quẹt chính thức)"""
    clean_note = note.strip()[:100] if note else None # Cắt ngắn note tránh spam dài

    # 1. Kiểm tra xem đã gửi cho người này bao giờ chưa (Mỗi cặp 1 lần duy nhất)
    sl_id = f"{guild_id}_{from_user}_{to_user}"
    existing = await superlikes_sent_col.find_one({"_id": sl_id})
    if existing:
        return {"kind": "already_sent"}

    # 2. Trừ ví Super Like (Atomic Update)
    spent = await sl_balances_col.update_one(
        {"_id": f"{guild_id}_{from_user}", "amount": {"$gte": 1}},
        {"$inc": {"amount": -1}}
    )
    
    if spent.modified_count == 0:
        return {"kind": "no_balance"}

    # 3. Ghi nhận đã gửi
    await superlikes_sent_col.update_one(
        {"_id": sl_id},
        {"$set": {
            "guildId": str(guild_id),
            "fromUserId": str(from_user),
            "toUserId": str(to_user),
            "note": clean_note,
            "createdAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )
    
    return {"kind": "sent"}

async def has_superliked(guild_id: str, from_user: str, to_user: str) -> bool:
    """Kiểm tra để vô hiệu hóa nút Super Like nếu đã bấm rồi"""
    sl = await superlikes_sent_col.find_one({"_id": f"{guild_id}_{from_user}_{to_user}"})
    return bool(sl)
