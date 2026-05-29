from core.state import State

# ==========================================
# LÕI BỘ NHỚ ĐỆM RAM CACHE (ANTI-TIMEOUT O(1))
# ==========================================
# Cấu trúc lưu trữ siêu tốc: { "guild_id": { "embed_name": doc_config_dict } }
FORMS_CACHE = {}

async def init_forms_cache():
    """
    [DEF - NEW INJECTION] 
    Tải toàn bộ cấu trúc cấu hình Form từ MongoDB lên RAM khi khởi động bot.
    """
    global FORMS_CACHE
    col = _get_forms_col()
    if col is not None:
        try:
            FORMS_CACHE.clear()
            cursor = col.find({})
            async for doc in cursor:
                gid = str(doc.get("guild_id"))
                name = str(doc.get("embed_name", "")).lower().strip()
                if gid and name:
                    if gid not in FORMS_CACHE:
                        FORMS_CACHE[gid] = {}
                    FORMS_CACHE[gid][name] = doc
            print("[FORMS-STORAGE] Bộ nhớ đệm RAM Cache đã nạp vèo vèo thành công!", flush=True)
        except Exception as e:
            print(f"[FORMS-STORAGE ERROR] Thất bại khi nạp đạn lên bộ nhớ RAM: {e}", flush=True)

# ==========================================
# DATABASE LOGIC (BẢO TỒN 100% DNA CỦA SẾP)
# ==========================================

def _get_forms_col():
    """
    [INDUSTRIAL PRO]
    Truy xuất trực tiếp collection 'forms' từ cỗ máy MongoDB.
    Đã tối ưu để tương thích với Proxy Attribute của hệ thống.
    """
    db = getattr(State.bot, "db", None)
    if not db: return None
    
    # Ưu tiên truy cập trực tiếp qua thuộc tính đã được ánh xạ
    try:
        return db.forms
    except Exception:
        # Kế hoạch dự phòng: Truy cập thẳng vào database thô
        raw_db = getattr(db, "db", None)
        if raw_db is not None:
            return raw_db["forms"]
    return None

async def get_form_config(guild_id: int, embed_name: str):
    """Lấy cấu hình Form (Ưu tiên RAM siêu tốc, có bảo hiểm DB)"""
    if not embed_name: return None
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    
    # 1. LỚP BẢO VỆ CHÍNH: Quét RAM Cache (O(1)) - Tránh Timeout
    if gid in FORMS_CACHE and name in FORMS_CACHE[gid]:
        return FORMS_CACHE[gid][name]
        
    # 2. LỚP BẢO HIỂM (FALLBACK): Nếu RAM rỗng, cầu cứu Database
    col = _get_forms_col()
    if col is not None:
        doc = await col.find_one({"guild_id": gid, "embed_name": name})
        if doc:
            # Đồng bộ ngược dữ liệu vừa tìm được lên RAM để các lần sau chạy xé gió
            if gid not in FORMS_CACHE:
                FORMS_CACHE[gid] = {}
            FORMS_CACHE[gid][name] = doc
            return doc
            
    return None

async def get_all_forms(guild_id: int):
    """
    [CẤY MỚI - ATK]
    Bốc toàn bộ danh sách Form của server để hiển thị Dashboard.
    Phục vụ lộ trình theo dõi setup thực tế của sếp.
    """
    gid = str(guild_id)
    col = _get_forms_col()
    if col is not None:
        cursor = col.find({"guild_id": gid})
        return await cursor.to_list(length=100)
    return []

async def update_form_base(guild_id: int, embed_name: str, title: str, log_id: str, thumbnail: bool):
    """Cập nhật thông tin khung (Base) của Form."""
    if not embed_name: return False
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        payload = {
            "form_title": title,
            "log_channel_id": log_id,
            "show_thumbnail": thumbnail
        }
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": payload},
            upsert=True
        )
        
        # [ĐỒNG BỘ RAM NÓNG LẬP TỨC] Chống lệch mạch hiển thị
        if gid not in FORMS_CACHE:
            FORMS_CACHE[gid] = {}
        if name not in FORMS_CACHE[gid]:
            FORMS_CACHE[gid][name] = {"guild_id": gid, "embed_name": name, "fields": {}}
            
        FORMS_CACHE[gid][name].update(payload)
        return True
    return False

async def update_form_field(guild_id: int, embed_name: str, slot: int, label: str, placeholder: str, required: bool):
    """Cập nhật dữ liệu chi tiết cho từng ô nhập liệu (Field Slot)."""
    if not embed_name: return False
    
    gid = str(guild_id)
    name = embed_name.lower().strip()
    col = _get_forms_col()
    
    if col is not None:
        field_data = {
            "label": label,
            "placeholder": placeholder,
            "required": required
        }
        # Cập nhật chính xác vào nested object 'fields' của Form
        await col.update_one(
            {"guild_id": gid, "embed_name": name},
            {"$set": {f"fields.{slot}": field_data}},
            upsert=True
        )
        
        # [ĐỒNG BỘ RAM NÓNG LẬP TỨC] Nạp đè chính xác ô nhập liệu vào bộ nhớ đệm
        if gid not in FORMS_CACHE:
            FORMS_CACHE[gid] = {}
        if name not in FORMS_CACHE[gid]:
            FORMS_CACHE[gid][name] = {"guild_id": gid, "embed_name": name, "fields": {}}
            
        if "fields" not in FORMS_CACHE[gid][name]:
            FORMS_CACHE[gid][name]["fields"] = {}
            
        FORMS_CACHE[gid][name]["fields"][str(slot)] = field_data
        return True
    return False
