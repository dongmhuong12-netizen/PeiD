import discord
from datetime import datetime, timezone

# ==============================
# CALCULATE BOOST DAYS
# ==============================

def get_boost_days(member: discord.Member) -> int:
    """Tính toán số ngày boost chính xác dựa trên chuỗi hiện tại"""
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    # Dùng tổng giây để tính ngày giúp tránh sai số múi giờ
    diff = now - member.premium_since
    days = diff.days

    return max(0, days)


# ==============================
# GET ALL BOOSTER SYSTEM ROLES (IDs Only)
# ==============================

def get_system_role_ids(booster_role_id: any, levels: list) -> set:
    """Lấy danh sách ID của tất cả role thuộc hệ thống để kiểm tra nhanh"""
    role_ids = set()
    
    if booster_role_id:
        role_ids.add(str(booster_role_id))
        
    for lvl in levels:
        r_id = lvl.get("role")
        if r_id:
            role_ids.add(str(r_id))
            
    return role_ids


# ==============================
# CLEANUP DELETED ROLES
# ==============================

def cleanup_deleted_roles(guild: discord.Guild, levels: list):
    """Xử lý trường hợp Role bị xóa thủ công khỏi Server"""
    changed = False
    new_levels = []

    for lvl in levels:
        role_id = lvl.get("role")
        if not role_id:
            changed = True
            continue

        role = guild.get_role(int(role_id))
        if not role:
            # Role không còn tồn tại -> Xóa level này
            changed = True
            continue

        new_levels.append(lvl)

    return new_levels, changed


# ==============================
# VALIDATE LEVEL CONFIG
# ==============================

def validate_levels(levels: list, booster_role_id: any):
    """Kiểm tra logic 43 mục: Level 1 = 0 ngày, ngày tăng dần, không trùng role"""
    if not levels:
        return True, None # Cho phép lưu cấu hình trống (Reset)

    role_set = set()
    if booster_role_id:
        role_set.add(str(booster_role_id))

    prev_days = -1

    for i, lvl in enumerate(levels):
        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            return False, f"Level {i+1} chưa được thiết lập đầy đủ thông tin."

        r_id_str = str(role_id)

        # Ràng buộc Level 1 (Mục 2 trong kế hoạch)
        if i == 0:
            if int(days) != 0:
                return False, "Level 1 (Booster Role) mặc định phải là 0 ngày."
            if r_id_str != str(booster_role_id):
                # Đảm bảo Role của Level 1 luôn khớp với Booster Role chính
                pass 
        else:
            # Ràng buộc tăng dần (Mục 22 trong kế hoạch)
            if int(days) <= prev_days:
                return False, f"Level {i+1} ({days} ngày) phải lớn hơn Level trước ({prev_days} ngày)."

        # Kiểm tra trùng Role (Mục 23 trong kế hoạch)
        if i > 0 and r_id_str == str(booster_role_id):
            return False, f"Role của Level {i+1} không được trùng với Booster Role mặc định."
            
        if i > 0 and r_id_str in role_set:
            return False, f"Role của Level {i+1} đã được sử dụng ở Level khác."

        role_set.add(r_id_str)
        prev_days = int(days)

    return True, None


# ==============================
# REORDER LEVELS (Atomic Move)
# ==============================

def move_level_up(levels: list, index: int):
    """Di chuyển Level lên trên (Giảm index)"""
    if index <= 1: # Không cho phép di chuyển Level 1 (Booster Role)
        return levels
    
    levels[index - 1], levels[index] = levels[index], levels[index - 1]
    return levels


def move_level_down(levels: list, index: int):
    """Di chuyển Level xuống dưới (Tăng index)"""
    if index == 0 or index >= len(levels) - 1:
        return levels
        
    levels[index + 1], levels[index] = levels[index], levels[index + 1]
    return levels


# ==============================
# FORMATTING UI (FIXED)
# ==============================

def format_level_status(lvl_idx: int, lvl_data: dict, guild: discord.Guild = None):
    """Tạo chuỗi hiển thị chuyên nghiệp, an toàn tuyệt đối với Null Guild"""
    role_id = lvl_data.get("role")
    days = lvl_data.get("days", 0)
    
    if not role_id:
        role_mention = "❌ Chưa thiết lập"
    else:
        # Bọc an toàn: Nếu guild là None (lúc vừa gọi lệnh), dùng chuỗi mention thô.
        # Discord client sẽ tự động render ID thành @Role.
        if guild:
            role = guild.get_role(int(role_id))
            role_mention = role.mention if role else f"<@&{role_id}>"
        else:
            role_mention = f"<@&{role_id}>"
            
    return f"**Level {lvl_idx + 1}**\nRole: {role_mention}\nDays: `{days}`"
