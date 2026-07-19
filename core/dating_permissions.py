import os
import discord
from core.dating_storage import db
from core.dating_cupid_commands import ALL_PERMISSIONS

# Collection quản lý chung cả Father và Cupid
admin_grants_col = db.admin_grants

def is_dev_user(user_id: str) -> bool:
    """Dev toàn cục - Quyền lực nằm trên cả Chủ Server. Lấy từ biến môi trường."""
    dev_id = os.getenv("DEV_USER_ID")
    return bool(dev_id and str(user_id) == dev_id)

async def authority_of(guild: discord.Guild, user_id: str) -> dict:
    """Đọc quyền thực tế của một người trong Server."""
    user_id = str(user_id)
    
    # 1. Dev toàn cục đứng trên mọi luật lệ
    if is_dev_user(user_id):
        return {"rank": "dev", "permissions": ALL_PERMISSIONS.copy(), "isFather": True}

    # 2. Chủ Server (Owner) là Father ngầm định, không ai phế truất được
    if str(guild.owner_id) == user_id:
        return {"rank": "owner", "permissions": ALL_PERMISSIONS.copy(), "isFather": True}

    # 3. Quét Database xem có phải Father / Cupid không
    grant = await admin_grants_col.find_one({"_id": f"{guild.id}_{user_id}"})
    
    if grant:
        if grant.get("role") == "FATHER":
            return {"rank": "father", "permissions": ALL_PERMISSIONS.copy(), "isFather": True}
        elif grant.get("role") == "CUPID" and grant.get("permissions"):
            return {"rank": "cupid", "permissions": grant["permissions"], "isFather": False}

    # 4. Dân thường
    return {"rank": "none", "permissions": [], "isFather": False}

async def is_father(guild: discord.Guild, user_id: str) -> bool:
    auth = await authority_of(guild, user_id)
    return auth["isFather"]

async def has_permission(guild: discord.Guild, user_id: str, perm: str) -> bool:
    auth = await authority_of(guild, user_id)
    return perm in auth["permissions"]

RANK_LABEL = {
    "dev": "Dev",
    "owner": "Chủ server",
    "father": "Father",
    "cupid": "Cupid",
    "none": "Không có quyền"
}

# ==========================================
# QUẢN LÝ NHÂN SỰ (Chỉ Father mới được gọi)
# ==========================================

async def promote_father(guild: discord.Guild, target_id: str, by_user_id: str) -> dict:
    """Phong tước Father"""
    target_id = str(target_id)
    bot_id = str(guild.me.id) if guild.me else None

    if target_id == str(guild.owner_id):
        return {"ok": False, "error": "Chủ server đã là Father sẵn rồi."}
    if is_dev_user(target_id):
        return {"ok": False, "error": "Người này đã là Father."}
    if target_id == bot_id:
        return {"ok": False, "error": "Không thể phong cho bot."}

    existing = await admin_grants_col.find_one({"_id": f"{guild.id}_{target_id}"})
    if existing and existing.get("role") == "FATHER":
        return {"ok": False, "error": "Người này đã là Father."}

    # Đè quyền thành FATHER, tự động bay màu rank CUPID nếu đang có
    await admin_grants_col.update_one(
        {"_id": f"{guild.id}_{target_id}"},
        {"$set": {
            "guildId": str(guild.id),
            "userId": target_id,
            "role": "FATHER",
            "permissions": ALL_PERMISSIONS.copy(),
            "grantedBy": str(by_user_id)
        }},
        upsert=True
    )
    return {"ok": True}

async def demote_father(guild: discord.Guild, target_id: str, by_user_id: str) -> dict:
    """Phế truất Father"""
    target_id, by_user_id = str(target_id), str(by_user_id)
    
    if target_id == str(guild.owner_id):
        return {"ok": False, "error": "Không thể gỡ quyền của chủ server."}
    if target_id == by_user_id:
        return {"ok": False, "error": "Không thể tự gỡ quyền của mình. Nhờ một Father khác hoặc chủ server."}

    res = await admin_grants_col.delete_one({"_id": f"{guild.id}_{target_id}", "role": "FATHER"})
    if res.deleted_count == 0:
        return {"ok": False, "error": "Người này không phải Father."}
        
    return {"ok": True}

async def set_cupid_permissions(guild: discord.Guild, target_id: str, permissions: list, by_user_id: str) -> dict:
    """Cấp quyền Cupid"""
    target_id = str(target_id)
    bot_id = str(guild.me.id) if guild.me else None

    if target_id == str(guild.owner_id):
        return {"ok": False, "error": "Chủ server đã có toàn quyền."}
    if is_dev_user(target_id):
        return {"ok": False, "error": "Người này là Father — đã có toàn quyền sẵn."}
    if target_id == bot_id:
        return {"ok": False, "error": "Không thể cấp quyền cho bot."}

    existing = await admin_grants_col.find_one({"_id": f"{guild.id}_{target_id}"})
    if existing and existing.get("role") == "FATHER":
        return {"ok": False, "error": "Người này là Father — đã có toàn quyền sẵn."}

    if not permissions:
        await admin_grants_col.delete_one({"_id": f"{guild.id}_{target_id}"})
        return {"ok": True}

    clean_perms = list(set([p for p in permissions if p in ALL_PERMISSIONS]))
    if not clean_perms:
        return {"ok": False, "error": "Quyền không hợp lệ."}

    await admin_grants_col.update_one(
        {"_id": f"{guild.id}_{target_id}"},
        {"$set": {
            "guildId": str(guild.id),
            "userId": target_id,
            "role": "CUPID",
            "permissions": clean_perms,
            "grantedBy": str(by_user_id)
        }},
        upsert=True
    )
    return {"ok": True}

async def list_staff(guild: discord.Guild) -> dict:
    """Hiển thị danh sách ban quản trị"""
    cursor = admin_grants_col.find({"guildId": str(guild.id)}).sort("createdAt", 1)
    
    fathers = []
    cupids = []
    
    async for grant in cursor:
        if is_dev_user(grant["userId"]):
            continue # Dev là tàng hình
            
        if grant.get("role") == "FATHER":
            fathers.append(grant)
        elif grant.get("role") == "CUPID":
            cupids.append(grant)

    return {
        "ownerId": str(guild.owner_id),
        "fathers": fathers,
        "cupids": cupids
    }

async def make_full_cupid(guild: discord.Guild, target_id: str, by_user_id: str) -> dict:
    """Cấp toàn quyền Cupid bằng 1 nốt nhạc"""
    return await set_cupid_permissions(guild, target_id, ALL_PERMISSIONS.copy(), by_user_id)
