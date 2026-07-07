import discord

DEFAULT_CONFIG = {
    "channel_id": None,
    "message": None,
    "embed_name": None,
    "trigger_status": None,
    "reward_role_id": None
}

async def get_servertag_config(bot, guild_id: int) -> dict:
    collection = bot.db.db['servertag_config']
    data = await collection.find_one({"guild_id": guild_id})
    if not data:
        return DEFAULT_CONFIG.copy()
    config = DEFAULT_CONFIG.copy()
    config.update(data)
    return config

async def update_servertag_config(bot, guild_id: int, key: str, value) -> None:
    collection = bot.db.db['servertag_config']
    await collection.update_one(
        {"guild_id": guild_id},
        {"$set": {key: value}},
        upsert=True
    )

# --- QUẢN LÝ MA TRẬN TRẠNG THÁI NGƯỜI DÙNG CHỐNG NHIỄU GATEWAY ---
async def get_user_servertag_state(bot, guild_id: int, user_id: int) -> dict:
    collection = bot.db.db['servertag_users']
    data = await collection.find_one({"guild_id": guild_id, "user_id": user_id})
    if not data:
        return {"has_clan": False, "has_status": False, "is_rewarded": False}
    return {
        "has_clan": data.get("has_clan", False),
        "has_status": data.get("has_status", False),
        "is_rewarded": data.get("is_rewarded", False)
    }

async def update_user_servertag_state(bot, guild_id: int, user_id: int, updates: dict) -> None:
    collection = bot.db.db['servertag_users']
    await collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": updates},
        upsert=True
    )
