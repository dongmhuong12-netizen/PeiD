from motor.motor_asyncio import AsyncIOMotorClient
import os

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client.voice_system
stations_col = db.setup_stations 
active_vcs_col = db.active_voices 

async def get_all_stations():
    cursor = stations_col.find({})
    return await cursor.to_list(length=None)

async def get_station(category_id: int):
    return await stations_col.find_one({"_id": category_id})

async def upsert_station(category_id: int, data: dict):
    await stations_col.update_one(
        {"_id": category_id},
        {"$set": data},
        upsert=True
    )

async def delete_station(category_id: int):
    await stations_col.delete_one({"_id": category_id})

async def get_active_voice(channel_id: int):
    return await active_vcs_col.find_one({"_id": channel_id})

async def add_active_voice(channel_id: int, owner_id: int, category_id: int):
    await active_vcs_col.insert_one({
        "_id": channel_id,
        "owner_id": owner_id,
        "category_id": category_id
    })

async def update_voice_owner(channel_id: int, new_owner_id: int):
    await active_vcs_col.update_one(
        {"_id": channel_id},
        {"$set": {"owner_id": new_owner_id}}
    )

async def remove_active_voice(channel_id: int):
    await active_vcs_col.delete_one({"_id": channel_id})
