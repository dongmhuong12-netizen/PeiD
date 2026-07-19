import datetime
from typing import Optional, Tuple, Dict, Any
from core.dating_storage import db, get_profile

# Định nghĩa các Collections
profiles_col = db.profiles
swipes_col = db.swipes
superlikes_col = db.superlikes_sent
blocks_col = db.blocks

def get_start_of_today() -> datetime.datetime:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

async def count_swipes_today(guild_id: str, user_id: str) -> int:
    """Đếm số lần quẹt trong ngày hôm nay"""
    start_of_day = get_start_of_today()
    return await swipes_col.count_documents({
        "guildId": str(guild_id),
        "fromUserId": str(user_id),
        "createdAt": {"$gte": start_of_day}
    })

async def _build_candidate_match_stage(me: dict) -> dict:
    """Xây dựng bộ lọc (WHERE clause) chuẩn logic của Yiyi"""
    guild_id = me.get("guildId")
    my_user_id = me.get("userId")
    my_gender = me.get("gender")
    my_age = me.get("age")
    my_seeking = me.get("seeking", [])
    my_seek_age_min = me.get("seekAgeMin", 18)
    my_seek_age_max = me.get("seekAgeMax", 99)

    # 1. Lọc những người mình đã quẹt (chống lặp)
    swiped_cursor = swipes_col.find({"guildId": guild_id, "fromUserId": my_user_id})
    swiped_ids = [doc["toUserId"] async for doc in swiped_cursor]

    # 2. Lọc những người đang bị Block (Cả 2 chiều, toàn cục)
    blocked_cursor_1 = blocks_col.find({"blockerId": my_user_id})
    blocked_cursor_2 = blocks_col.find({"blockedId": my_user_id})
    blocked_ids = set()
    async for doc in blocked_cursor_1: blocked_ids.add(doc["blockedId"])
    async for doc in blocked_cursor_2: blocked_ids.add(doc["blockerId"])

    exclude_users = list(set(swiped_ids) | blocked_ids | {my_user_id})

    # TRÁI TIM THUẬT TOÁN: BỘ LỌC 2 CHIỀU
    return {
        "guildId": guild_id,
        "status": "ACTIVE",
        "userId": {"$nin": exclude_users},
        "gender": {"$in": my_seeking},          # Họ phải có giới tính mình đang tìm
        "age": {"$gte": my_seek_age_min, "$lte": my_seek_age_max}, # Tuổi họ phải vừa ý mình
        "seeking": my_gender,                   # Minh phải có giới tính mà HỌ đang tìm
        "seekAgeMin": {"$lte": my_age},         # Tuổi mình phải lớn hơn min của họ
        "seekAgeMax": {"$gte": my_age}          # Tuổi mình phải nhỏ hơn max của họ
    }

async def count_pool(me: dict) -> int:
    """Đếm tổng số "cá" còn lại trong hồ thỏa mãn điều kiện"""
    match_stage = await _build_candidate_match_stage(me)
    return await profiles_col.count_documents(match_stage)

async def next_candidate(me: dict) -> Optional[Tuple[Dict[Any, Any], Optional[Dict[str, str]]]]:
    """
    Rút 1 ứng viên tiếp theo dựa trên thuật toán xếp hạng NoSQL.
    Trả về: (profile_dict, superliked_you_dict) hoặc None.
    """
    guild_id = me.get("guildId")
    my_user_id = me.get("userId")
    my_tags = me.get("tags", [])
    
    match_stage = await _build_candidate_match_stage(me)
    three_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)

    # ===============================================================
    # PIPELINE SIÊU CẤP MONGODB (THAY THẾ CHUỖI ORDER BY CỦA PRISMA)
    # ===============================================================
    pipeline = [
        {"$match": match_stage},
        
        # Bước 1: Lookup xem họ có Super Like mình không (Gắn cờ ưu tiên 1)
        {
            "$lookup": {
                "from": "superlikes_sent",
                "let": {"candidateId": "$userId"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$guildId", guild_id]},
                                {"$eq": ["$fromUserId", "$$candidateId"]},
                                {"$eq": ["$toUserId", my_user_id]}
                            ]
                        }
                    }}
                ],
                "as": "superlikes_received"
            }
        },
        
        # Bước 2: Thêm các cột ảo (Fields) để phục vụ việc sắp xếp
        {
            "$addFields": {
                # Cờ: 1 nếu đã gửi Super Like, 0 nếu không
                "has_superliked": {"$cond": [{"$gt": [{"$size": "$superlikes_received"}, 0]}, 1, 0]},
                
                # Cờ Bucket Hiển thị: timesShown chia nguyên cho 5
                "exposure_bucket": {"$floor": {"$divide": [{"$ifNull": ["$timesShown", 0]}, 5]}},
                
                # Cờ Hoạt động: 0 nếu active trong 3 ngày qua, 1 nếu offline lâu hơn
                "is_stale": {"$cond": [{"$gt": ["$lastActiveAt", three_days_ago]}, 0, 1]},
                
                # Đếm số Tag trùng khớp
                "tag_match_count": {"$size": {"$setIntersection": [{"$ifNull": ["$tags", []]}, my_tags]}}
            }
        },
        
        # Bước 3: Thuật toán Sắp Xếp Trọng Số
        {
            "$sort": {
                "has_superliked": -1,   # 1. Thằng nào cúng tiền Super Like thì auto lên đầu
                "tag_match_count": -1,  # 2. Hợp Gu Tag chung thì lên
                "exposure_bucket": 1,   # 3. Kẻ chưa được Show bao giờ thì được ưu tiên (Chống chìm mảng)
                "is_stale": 1           # 4. Tài khoản active dạo gần đây ưu tiên xếp trên tụi chết trôi
            }
        },
        {"$limit": 1} # Chốt hạ lấy đúng 1 mạng đầu tiên
    ]

    cursor = profiles_col.aggregate(pipeline)
    candidates = await cursor.to_list(length=1)
    
    if not candidates:
        return None
        
    candidate = candidates[0]
    candidate_id = candidate.get("id")
    
    # Cộng dồn bộ đếm (Tăng số lần bị "phơi bày" lên 1)
    await profiles_col.update_one(
        {"_id": candidate_id},
        {"$inc": {"timesShown": 1}}
    )
    
    # Trích xuất Note Super Like (Nếu có)
    super_liked_you = None
    if candidate.get("has_superliked") == 1:
        note = candidate["superlikes_received"][0].get("note")
        super_liked_you = {"note": note}
        
    # Xóa các cột ảo trước khi trả về để giữ code sạch
    for key in ["superlikes_received", "has_superliked", "exposure_bucket", "is_stale", "tag_match_count"]:
        candidate.pop(key, None)

    return candidate, super_liked_you

async def get_destiny_candidate(me: dict) -> Optional[Tuple[Dict[Any, Any], None]]:
    """Cơ chế Vận Mệnh: Chỉ dựa vào Tag và Active, bỏ qua bucket và Super Like"""
    match_stage = await _build_candidate_match_stage(me)
    my_tags = me.get("tags", [])
    
    pipeline = [
        {"$match": match_stage},
        {"$addFields": {
            "tag_match_count": {"$size": {"$setIntersection": [{"$ifNull": ["$tags", []]}, my_tags]}}
        }},
        {"$sort": {
            "tag_match_count": -1, 
            "lastActiveAt": -1
        }},
        {"$limit": 1}
    ]
    
    cursor = profiles_col.aggregate(pipeline)
    candidates = await cursor.to_list(length=1)
    
    if not candidates:
        return None
        
    candidate = candidates[0]
    candidate.pop("tag_match_count", None)
    return candidate, None

async def touch_activity(guild_id: str, user_id: str):
    """Cập nhật mốc thời gian online lần cuối để hệ thống chấm điểm mượt hơn"""
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$set": {"lastActiveAt": datetime.datetime.now(datetime.timezone.utc)}}
    )
