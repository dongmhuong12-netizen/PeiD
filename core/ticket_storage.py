from core.state import State

async def get_ticket_config(guild_id: int):
    """Truy xuất cấu hình Ticket của server từ MongoDB."""
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db:
        # Sử dụng collection 'configs' với module định danh 'ticket'
        doc = await db.configs.find_one({"guild_id": gid, "module": "ticket"})
        return doc.get("settings") if doc else None
    return None

async def update_ticket_config(guild_id: int, config_data: dict):
    """Đồng bộ cấu hình Ticket (Category/Roles/Log) lên Cloud Atlas."""
    gid = str(guild_id)
    db = getattr(State.bot, "db", None)
    if db:
        await db.configs.update_one(
            {"guild_id": gid, "module": "ticket"},
            {"$set": {"settings": config_data}},
            upsert=True
        )
        return True
    return False
