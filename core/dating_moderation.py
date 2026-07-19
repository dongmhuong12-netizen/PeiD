import datetime
from core.dating_storage import db, get_profile
from core.dating_onboarding import sync_status

profiles_col = db.profiles
swipes_col = db.swipes
matches_col = db.matches
reports_col = db.reports

async def reset_user_swipes(guild_id: str, user_id: str) -> dict:
    """Xóa lịch sử lướt + match của một người trong server (Làm mới hoàn toàn)"""
    guild_id, user_id = str(guild_id), str(user_id)
    
    # Xóa cả 2 chiều Swipe
    swipes_res = await swipes_col.delete_many({
        "guildId": guild_id, 
        "$or": [{"fromUserId": user_id}, {"toUserId": user_id}]
    })
    
    # Xóa cả 2 chiều Match
    matches_res = await matches_col.delete_many({
        "guildId": guild_id, 
        "$or": [{"userAId": user_id}, {"userBId": user_id}]
    })
    
    return {"swipes": swipes_res.deleted_count, "matches": matches_res.deleted_count}

async def open_reports(guild_id: str, limit: int = 10) -> list:
    """Lấy danh sách các báo cáo đang cần xử lý"""
    cursor = reports_col.find({
        "guildId": str(guild_id), 
        "status": "OPEN"
    }).sort("createdAt", 1).limit(limit)
    return await cursor.to_list(length=limit)

async def reports_against(guild_id: str, user_id: str) -> list:
    """Gộp toàn bộ báo cáo nhắm vào 1 người cụ thể"""
    cursor = reports_col.find({
        "guildId": str(guild_id), 
        "reportedId": str(user_id)
    }).sort("createdAt", -1).limit(20)
    return await cursor.to_list(length=20)

async def resolve_reports(guild_id: str, reported_id: str, action: str, by_user_id: str) -> dict:
    """Đóng report (action: 'resolve' = xử lý xong / 'dismiss' = không cơ sở)"""
    guild_id, reported_id, by_user_id = str(guild_id), str(reported_id), str(by_user_id)
    
    open_count = await reports_col.count_documents({
        "guildId": guild_id, 
        "reportedId": reported_id, 
        "status": "OPEN"
    })
    
    if open_count == 0:
        return {"ok": False, "error": "Người này không có báo cáo nào đang mở."}
        
    status = "RESOLVED" if action == "resolve" else "DISMISSED"
    now = datetime.datetime.now(datetime.timezone.utc)
    
    await reports_col.update_many(
        {"guildId": guild_id, "reportedId": reported_id, "status": "OPEN"},
        {"$set": {"status": status, "resolvedBy": by_user_id, "resolvedAt": now}}
    )
    
    # Nếu đánh dấu vô tội (dismiss) -> Gỡ trạng thái ẩn hồ sơ (nếu đang bị)
    if action == "dismiss":
        profile = await get_profile(guild_id, reported_id)
        if profile and profile.get("status") == "UNDER_REVIEW":
            await profiles_col.update_one(
                {"_id": profile["_id"]},
                {"$set": {"status": "DRAFT"}}
            )
            # Tự động soi xét bật lại sáng đèn nếu hồ sơ điền đầy đủ
            await sync_status(guild_id, reported_id)
            return {"ok": True, "note": f"Đã bỏ ẩn hồ sơ ({open_count} báo cáo được đánh dấu không có cơ sở)."}
            
    return {"ok": True, "note": f"Đã đóng {open_count} báo cáo."}

async def ban_profile(guild_id: str, user_id: str, by_user_id: str) -> dict:
    """Trảm! Khóa hồ sơ vi phạm khỏi mạng lưới"""
    guild_id, user_id, by_user_id = str(guild_id), str(user_id), str(by_user_id)
    
    profile = await get_profile(guild_id, user_id)
    if not profile:
        return {"ok": False, "error": "Người này không có hồ sơ."}
    if profile.get("status") == "BANNED":
        return {"ok": False, "error": "Hồ sơ này đã bị cấm rồi."}
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Cấm hồ sơ
    await profiles_col.update_one(
        {"_id": profile["_id"]},
        {"$set": {"status": "BANNED"}}
    )
    
    # Đóng luôn tất cả các báo cáo đang mở liên quan đến người này (Không cần duyệt nữa)
    await reports_col.update_many(
        {"guildId": guild_id, "reportedId": user_id, "status": "OPEN"},
        {"$set": {"status": "RESOLVED", "resolvedBy": by_user_id, "resolvedAt": now}}
    )
    
    return {"ok": True, "note": "Hồ sơ đã bị cấm và biến khỏi phần lướt của mọi người."}

async def unban_profile(guild_id: str, user_id: str) -> dict:
    """Ân xá! Gỡ cấm cho hồ sơ"""
    guild_id, user_id = str(guild_id), str(user_id)
    
    profile = await get_profile(guild_id, user_id)
    if not profile:
        return {"ok": False, "error": "Người này không có hồ sơ."}
        
    if profile.get("status") not in ["BANNED", "UNDER_REVIEW"]:
        return {"ok": False, "error": "Hồ sơ này không bị cấm."}
        
    await profiles_col.update_one(
        {"_id": profile["_id"]},
        {"$set": {"status": "DRAFT"}}
    )
    
    # Test lại điều kiện xem có đủ điệu kiện hoạt động luôn không
    await sync_status(guild_id, user_id)
    
    fresh = await get_profile(guild_id, user_id)
    if fresh and fresh.get("status") == "ACTIVE":
        return {"ok": True, "note": "Hồ sơ đã hoạt động trở lại."}
    else:
        return {"ok": True, "note": "Đã bỏ cấm. Hồ sơ chưa hiện lại vì còn thiếu thông tin — họ cần tự hoàn tất."}
