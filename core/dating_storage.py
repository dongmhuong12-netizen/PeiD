import os
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# KHỞI TẠO KẾT NỐI MONGODB
# ==========================================
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client.dating_system

# Định nghĩa các Collections (Tương đương Table trong SQL)
guild_configs_col = db.guild_configs
profiles_col = db.profiles
swipes_col = db.swipes
superlikes_col = db.superlikes_sent
matches_col = db.matches
blocks_col = db.blocks
reports_col = db.reports
sl_balances_col = db.sl_balances
sl_grants_col = db.sl_grants
admin_grants_col = db.admin_grants # Gộp chung Father và Cupid
crushes_col = db.secret_crushes
quiz_states_col = db.quiz_states
glyphs_col = db.guild_glyphs

# ==========================================
# 1. CẤU HÌNH SERVER (GuildConfig)
# ==========================================
async def get_guild_config(guild_id: str) -> dict:
    return await guild_configs_col.find_one({"_id": str(guild_id)})

async def upsert_guild_config(guild_id: str, data: dict):
    data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc)
    await guild_configs_col.update_one(
        {"_id": str(guild_id)},
        {"$set": data, "$setOnInsert": {"createdAt": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True
    )

# ==========================================
# 2. HỒ SƠ NGƯỜI DÙNG (Profile + Socials + Prompts)
# ==========================================
async def get_profile(guild_id: str, user_id: str) -> dict:
    """Lấy Profile, Scope mặc định theo Guild"""
    return await profiles_col.find_one({"_id": f"{guild_id}_{user_id}"})

async def upsert_profile(guild_id: str, user_id: str, data: dict):
    """
    Data đầu vào có thể chứa luôn cả 'socials': [] và 'prompts': []
    Tối ưu hóa hoàn toàn NoSQL Document.
    """
    data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc)
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {
            "$set": data, 
            "$setOnInsert": {
                "guildId": str(guild_id),
                "userId": str(user_id),
                "createdAt": datetime.datetime.now(datetime.timezone.utc),
                "timesShown": 0,
                "status": "DRAFT",
                "socials": [], # Embed data thay vì tạo bảng phụ
                "prompts": []  # Embed data thay vì tạo bảng phụ
            }
        },
        upsert=True
    )

# ==========================================
# 3. HỆ THỐNG QUẸT (Swipe & SuperLike)
# ==========================================
async def add_swipe(guild_id: str, from_user: str, to_user: str, action: str):
    """action: 'LIKE' hoặc 'PASS'"""
    await swipes_col.update_one(
        {"_id": f"{guild_id}_{from_user}_{to_user}"},
        {"$set": {
            "guildId": str(guild_id),
            "fromUserId": str(from_user),
            "toUserId": str(to_user),
            "action": action,
            "createdAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )

async def check_swipe(guild_id: str, from_user: str, to_user: str) -> dict:
    return await swipes_col.find_one({"_id": f"{guild_id}_{from_user}_{to_user}"})

async def add_superlike(guild_id: str, from_user: str, to_user: str, note: str = None):
    await superlikes_col.update_one(
        {"_id": f"{guild_id}_{from_user}_{to_user}"},
        {"$set": {
            "guildId": str(guild_id),
            "fromUserId": str(from_user),
            "toUserId": str(to_user),
            "note": note,
            "createdAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )

# ==========================================
# 4. HỆ THỐNG GHÉP ĐÔI (Match)
# ==========================================
def _get_match_id(guild_id: str, user1: str, user2: str) -> str:
    """Tự động sắp xếp A < B để sinh ra ID chung duy nhất, chống Race Condition"""
    a, b = sorted([str(user1), str(user2)])
    return f"{guild_id}_{a}_{b}"

async def create_match(guild_id: str, user_a: str, user_b: str, opt_in_hours: int = 24):
    match_id = _get_match_id(guild_id, user_a, user_b)
    userA_id, userB_id = sorted([str(user_a), str(user_b)])
    
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=opt_in_hours)
    
    await matches_col.update_one(
        {"_id": match_id},
        {"$setOnInsert": {
            "guildId": str(guild_id),
            "userAId": userA_id,
            "userBId": userB_id,
            "status": "PENDING_OPT_IN",
            "userAReady": False,
            "userBReady": False,
            "threadId": None,
            "optInExpiresAt": expires_at,
            "createdAt": datetime.datetime.now(datetime.timezone.utc),
            "lastActivityAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )
    return match_id

async def get_match(match_id: str) -> dict:
    return await matches_col.find_one({"_id": match_id})

async def update_match(match_id: str, data: dict):
    data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc)
    await matches_col.update_one({"_id": match_id}, {"$set": data})

# ==========================================
# 5. AN TOÀN & BÁO CÁO (Blocks & Reports)
# ==========================================
async def block_user(blocker_id: str, blocked_id: str):
    """Block này là TOÀN CỤC (Global), không theo guild"""
    await blocks_col.update_one(
        {"_id": f"{blocker_id}_{blocked_id}"},
        {"$setOnInsert": {
            "blockerId": str(blocker_id),
            "blockedId": str(blocked_id),
            "createdAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )

async def check_block(user_a: str, user_b: str) -> bool:
    """Kiểm tra xem A có block B, hoặc B có block A không"""
    block1 = await blocks_col.find_one({"_id": f"{user_a}_{user_b}"})
    block2 = await blocks_col.find_one({"_id": f"{user_b}_{user_a}"})
    return bool(block1 or block2)

async def create_report(guild_id: str, reporter_id: str, reported_id: str, reason: str, snapshot: dict = None):
    await reports_col.update_one(
        {"_id": f"{guild_id}_{reporter_id}_{reported_id}"}, # Chống spam 1 người report 1 người nhiều lần
        {"$setOnInsert": {
            "guildId": str(guild_id),
            "reporterId": str(reporter_id),
            "reportedId": str(reported_id),
            "reason": reason,
            "snapshot": snapshot,
            "status": "OPEN",
            "createdAt": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )

# ==========================================
# 6. PHÂN QUYỀN HỆ THỐNG (Father / Cupid)
# ==========================================
async def get_admin_grant(guild_id: str, user_id: str) -> dict:
    """Trả về dict chứa role ('FATHER' hoặc 'CUPID') và danh sách permissions"""
    return await admin_grants_col.find_one({"_id": f"{guild_id}_{user_id}"})

async def upsert_admin_grant(guild_id: str, user_id: str, role: str, permissions: list, granted_by: str = None):
    await admin_grants_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$set": {
            "guildId": str(guild_id),
            "userId": str(user_id),
            "role": role, # "FATHER" hoặc "CUPID"
            "permissions": permissions,
            "grantedBy": granted_by,
            "updatedAt": datetime.datetime.now(datetime.timezone.utc)
        }, "$setOnInsert": {"createdAt": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True
    )

# ==========================================
# 7. MINIGAME TRẮC NGHIỆM (QuizState)
# ==========================================
async def get_quiz_state(match_id: str) -> dict:
    return await quiz_states_col.find_one({"_id": match_id})

async def upsert_quiz_state(match_id: str, data: dict):
    data["updatedAt"] = datetime.datetime.now(datetime.timezone.utc)
    await quiz_states_col.update_one(
        {"_id": match_id},
        {"$set": data},
        upsert=True
    )
