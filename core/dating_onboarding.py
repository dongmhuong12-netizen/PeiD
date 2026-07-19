import datetime
import discord
from core.dating_storage import db, get_profile
from core.dating_photo import validate_photo
from core.dating_prompts import is_valid_prompt_key, REQUIRED_PROMPTS
from core.dating_socials import parse_social

profiles_col = db.profiles

MIN_AGE = 18
MAX_AGE = 99

VALID_GENDERS = ["MALE", "FEMALE", "NONBINARY", "OTHER"]

def missing_fields(p: dict) -> list:
    """Kiểm tra xem profile còn thiếu gì để được lên sóng (ACTIVE)"""
    out = []
    if not p.get("photoUrl"):
        out.append("Chưa có ảnh đại diện")
        
    prompts = p.get("prompts", [])
    if len(prompts) < REQUIRED_PROMPTS:
        out.append(f"Cần trả lời {REQUIRED_PROMPTS} câu hỏi (mới có {len(prompts)})")
        
    if not p.get("seeking"):
        out.append("Chưa chọn đối tượng muốn tìm")
        
    if not p.get("consentAt"):
        out.append("Chưa xác nhận điều khoản")
        
    return out

async def sync_status(guild_id: str, user_id: str):
    """Bật/tắt trạng thái ACTIVE theo độ hoàn chỉnh của Profile."""
    p = await get_profile(guild_id, user_id)
    if not p:
        return
        
    status = p.get("status")
    # Không can thiệp nếu Mod đang khóa mõm hoặc user tự ẩn mình
    if status in ["UNDER_REVIEW", "BANNED", "PAUSED"]:
        return

    next_status = "ACTIVE" if len(missing_fields(p)) == 0 else "DRAFT"
    
    if status != next_status:
        await profiles_col.update_one(
            {"_id": f"{guild_id}_{user_id}"}, 
            {"$set": {"status": next_status}}
        )

async def handle_basics(
    guild_id: str, 
    user_id: str, 
    name: str, 
    age_raw: str, 
    gender: str, 
    seeking: list, 
    photo_attachment: discord.Attachment = None
) -> dict:
    """Xử lý form tạo/sửa thông tin cơ bản"""
    name = name.strip()
    
    try:
        age = int(str(age_raw).strip())
    except ValueError:
        return {"ok": False, "error": "Tuổi phải là số."}
        
    if age < MIN_AGE:
        return {
            "ok": False,
            "error": f"Bot này chỉ dành cho người từ {MIN_AGE} tuổi trở lên.\nĐây là giới hạn cứng, không có ngoại lệ."
        }
    if age > MAX_AGE:
        return {"ok": False, "error": "Tuổi không hợp lệ."}

    if not gender or gender not in VALID_GENDERS:
        return {"ok": False, "error": "Giới tính không hợp lệ."}
        
    seek = [s for s in seeking if s in VALID_GENDERS]
    if not seek:
        return {"ok": False, "error": "Chọn ít nhất một đối tượng."}

    photo_url = None
    if photo_attachment:
        res = validate_photo(photo_attachment)
        if not res["ok"]:
            return {"ok": False, "error": res["error"]}
        photo_url = res["url"]

    existing = await get_profile(guild_id, user_id)

    if not existing and not photo_url:
        return {"ok": False, "error": "Cần một ảnh đại diện để tạo hồ sơ."}

    # Chuẩn bị Data
    now = datetime.datetime.now(datetime.timezone.utc)
    update_data = {
        "displayName": name,
        "age": age,
        "gender": gender,
        "seeking": seek,
        "lastActiveAt": now
    }
    
    if photo_url:
        update_data["photoUrl"] = photo_url
        
    if not existing or not existing.get("consentAt"):
        update_data["consentAt"] = now

    # Upsert Profile
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {
            "$set": update_data,
            "$setOnInsert": {
                "guildId": str(guild_id),
                "userId": str(user_id),
                "createdAt": now,
                "timesShown": 0,
                "status": "DRAFT",
                "socials": [],
                "prompts": []
            }
        },
        upsert=True
    )

    await sync_status(guild_id, user_id)
    return {"ok": True}

async def handle_prompts(
    guild_id: str, 
    user_id: str, 
    picked_prompts: list, # List of dict: [{"key": "...", "answer": "..."}, ...]
    bio: str = None
) -> dict:
    """Xử lý lưu trữ Bio và các câu hỏi thả thính"""
    profile = await get_profile(guild_id, user_id)
    if not profile:
        return {"ok": False, "error": "Bạn chưa có hồ sơ. Dùng lệnh setup trước."}

    valid_picked = []
    seen_keys = set()
    
    for idx, p in enumerate(picked_prompts):
        key = p.get("key")
        answer = str(p.get("answer", "")).strip()
        
        if not key or not is_valid_prompt_key(key):
            return {"ok": False, "error": "Câu hỏi không hợp lệ."}
        if not answer:
            return {"ok": False, "error": "Chưa trả lời đủ."}
        if key in seen_keys:
            return {"ok": False, "error": "Chọn hai câu hỏi khác nhau nhé."}
            
        seen_keys.add(key)
        valid_picked.append({
            "promptKey": key,
            "answer": answer,
            "position": idx
        })

    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Ghi đè toàn bộ mảng prompts bằng mảng mới
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$set": {
            "prompts": valid_picked,
            "bio": bio.strip() if bio else None,
            "lastActiveAt": now
        }}
    )

    await sync_status(guild_id, user_id)
    return {"ok": True}

async def handle_prefs(
    guild_id: str, 
    user_id: str, 
    seeking: list, 
    min_age_raw: str, 
    max_age_raw: str
) -> dict:
    """Xử lý thiết lập bộ lọc tìm kiếm của user"""
    seek = [s for s in seeking if s in VALID_GENDERS]
    if not seek:
        return {"ok": False, "error": "Chọn ít nhất một đối tượng."}
        
    try:
        min_age = int(str(min_age_raw).strip())
        max_age = int(str(max_age_raw).strip())
    except ValueError:
        return {"ok": False, "error": "Tuổi phải là số."}

    # Chặn cứng ở 18 tuổi: không thể đặt bộ lọc tìm trẻ vị thành niên
    if min_age < MIN_AGE:
        return {"ok": False, "error": f"Tuổi tối thiểu không thể dưới {MIN_AGE}."}
    if max_age > MAX_AGE:
        return {"ok": False, "error": "Tuổi tối đa không hợp lệ."}
    if min_age > max_age:
        return {"ok": False, "error": "Tuổi tối thiểu phải nhỏ hơn tuổi tối đa."}

    res = await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$set": {
            "seeking": seek,
            "seekAgeMin": min_age,
            "seekAgeMax": max_age,
            "lastActiveAt": datetime.datetime.now(datetime.timezone.utc)
        }}
    )
    
    if res.matched_count == 0:
        return {"ok": False, "error": "Bạn chưa có hồ sơ."}
        
    return {"ok": True}

async def handle_social(
    guild_id: str, 
    user_id: str, 
    platform: str, 
    raw_value: str
) -> dict:
    """Xử lý thêm/xóa link mạng xã hội của User"""
    profile = await get_profile(guild_id, user_id)
    if not profile:
        return {"ok": False, "error": "Bạn chưa có hồ sơ."}

    raw = str(raw_value).strip() if raw_value else ""

    # Nếu người dùng để trống -> Xóa link nền tảng đó
    if not raw:
        await profiles_col.update_one(
            {"_id": f"{guild_id}_{user_id}"},
            {"$pull": {"socials": {"platform": platform}}}
        )
        return {"ok": True}

    # Kiểm tra Regex chống link bẩn
    parsed = parse_social(platform, raw)
    if not parsed["ok"]:
        return {"ok": False, "error": parsed["error"]}

    # Xóa link cũ của platform đó (nếu có) rồi nhét link mới vào
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$pull": {"socials": {"platform": platform}}}
    )
    await profiles_col.update_one(
        {"_id": f"{guild_id}_{user_id}"},
        {"$push": {"socials": {"platform": platform, "value": parsed["handle"]}}}
    )

    return {"ok": True}
