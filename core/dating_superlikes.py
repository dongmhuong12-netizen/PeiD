import datetime
from core.dating_storage import db

sl_balances_col = db.sl_balances
sl_grants_col = db.sl_grants

MAX_GRANT_PER_CALL = 50

async def give_superlikes(guild_id: str, by_user_id: str, to_user_id: str, amount: float, reason: str = None) -> dict:
    """Cấp hoặc Thu hồi Super Like"""
    guild_id, to_user_id = str(guild_id), str(to_user_id)
    amount = int(amount)

    if amount == 0:
        return {"ok": False, "error": "Số lượng phải khác 0."}
        
    if abs(amount) > MAX_GRANT_PER_CALL:
        return {
            "ok": False,
            "error": f"Tối đa {MAX_GRANT_PER_CALL} mỗi lần. Cần nhiều hơn thì chạy lệnh vài lần."
        }

    # Kiểm tra số dư hiện tại
    balance_doc = await sl_balances_col.find_one({"_id": f"{guild_id}_{to_user_id}"})
    before = balance_doc.get("amount", 0) if balance_doc else 0

    # Chống thu hồi lố tay sinh ra số âm
    delta = amount if amount > 0 else -min(before, abs(amount))
    if delta == 0:
        return {"ok": False, "error": "Người này không còn Super Like nào để thu hồi."}

    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Cập nhật số dư
    await sl_balances_col.update_one(
        {"_id": f"{guild_id}_{to_user_id}"},
        {
            "$inc": {"amount": delta},
            "$setOnInsert": {"guildId": guild_id, "userId": to_user_id}
        },
        upsert=True
    )
    
    # Lấy số dư mới tinh
    new_balance_doc = await sl_balances_col.find_one({"_id": f"{guild_id}_{to_user_id}"})
    new_balance = new_balance_doc.get("amount", 0)

    # 2. Ghi vào Sổ Nam Tào (Lịch sử cấp phát)
    await sl_grants_col.insert_one({
        "guildId": guild_id,
        "byUserId": str(by_user_id),
        "toUserId": to_user_id,
        "amount": delta,
        "reason": reason.strip()[:200] if reason else None,
        "createdAt": now
    })

    return {"ok": True, "balance": new_balance, "delta": delta}

async def get_balance(guild_id: str, user_id: str) -> int:
    """Soi ví Super Like của thành viên"""
    row = await sl_balances_col.find_one({"_id": f"{str(guild_id)}_{str(user_id)}"})
    return row.get("amount", 0) if row else 0

async def recent_grants(guild_id: str, limit: int = 15) -> list:
    """Xem ai vừa được cấp Super Like gần đây"""
    cursor = sl_grants_col.find({"guildId": str(guild_id)}).sort("createdAt", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def grants_by_staff(guild_id: str, since_days: int = 30) -> list:
    """Báo cáo Thống kê: Soi các Admin có đang tuồn vật phẩm ra ngoài không"""
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)
    
    pipeline = [
        {"$match": {
            "guildId": str(guild_id),
            "createdAt": {"$gte": since},
            "amount": {"$gt": 0}
        }},
        {"$group": {
            "_id": "$byUserId",
            "total_amount": {"$sum": "$amount"},
            "grant_count": {"$sum": 1}
        }},
        {"$sort": {"total_amount": -1}}
    ]
    
    cursor = sl_grants_col.aggregate(pipeline)
    return await cursor.to_list(length=None)
