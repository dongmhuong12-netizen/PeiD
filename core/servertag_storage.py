import discord

DEFAULT_CONFIG = {
    "channel_id": None,
    "message": None,
    "embed_name": None,
    "trigger": None,
    "reward_role_id": None
}

# ==========================================
# QUẢN LÝ CẤU HÌNH ĐỘC LẬP (STATUS & CLAN TAG)
# ==========================================
async def get_tag_config(bot, guild_id: int, tag_type: str) -> dict:
    """
    Lấy cấu hình riêng biệt dựa trên tag_type ('status' hoặc 'clan')
    """
    collection = bot.db.db['tag_config']
    data = await collection.find_one({"guild_id": guild_id, "tag_type": tag_type})
    if not data:
        return DEFAULT_CONFIG.copy()
    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config

async def update_tag_config(bot, guild_id: int, tag_type: str, key: str, value) -> None:
    collection = bot.db.db['tag_config']
    await collection.update_one(
        {"guild_id": guild_id, "tag_type": tag_type},
        {"$set": {key: value}},
        upsert=True
    )

# ==========================================
# QUẢN LÝ MA TRẬN TRẠNG THÁI NGƯỜI DÙNG (CROSS-VALIDATION)
# ==========================================
async def get_user_tag_state(bot, guild_id: int, user_id: int) -> dict:
    collection = bot.db.db['tag_users']
    data = await collection.find_one({"guild_id": guild_id, "user_id": user_id})
    if not data:
        return {
            "has_clan": False, 
            "has_status": False, 
            "status_rewarded": False, 
            "clan_rewarded": False
        }
    return {
        "has_clan": data.get("has_clan", False),
        "has_status": data.get("has_status", False),
        "status_rewarded": data.get("status_rewarded", False),
        "clan_rewarded": data.get("clan_rewarded", False)
    }

async def update_user_tag_state(bot, guild_id: int, user_id: int, updates: dict) -> None:
    collection = bot.db.db['tag_users']
    await collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": updates},
        upsert=True
    )
