import asyncio
from core.state import State

# Cache RAM để phản hồi reaction thần tốc (O(1))
_reaction_cache = {}

async def get_reaction_config(guild_id: int, message_id: str):
    """Lấy cấu hình reaction từ RAM hoặc Cloud Atlas."""
    gid = str(guild_id)
    mid = str(message_id)
    
    # 1. Ưu tiên RAM (Stateless fallback)
    if mid not in _reaction_cache:
        db = getattr(State.bot, "db", None)
        if db:
            # Truy vấn từ collection 'reactions' - tách biệt hoàn toàn với embed
            doc = await db.reactions.find_one({"guild_id": gid, "message_id": mid})
            if doc:
                _reaction_cache[mid] = doc.get("config", {})
    
    return _reaction_cache.get(mid)

async def save_reaction_config(guild_id: int, message_id: str, config: dict):
    """Lưu cấu hình reaction (Emoji -> Role) vào Cloud Atlas."""
    gid = str(guild_id)
    mid = str(message_id)
    
    # Ghi RAM trước (Source of Truth tạm thời)
    _reaction_cache[mid] = config
    
    db = getattr(State.bot, "db", None)
    if db:
        await db.reactions.update_one(
            {"guild_id": gid, "message_id": mid},
            {"$set": {"config": config}},
            upsert=True
        )
    return True
