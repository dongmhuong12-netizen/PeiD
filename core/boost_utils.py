import discord
from datetime import datetime, timezone
from core.greet_storage import get_section

# ==============================
# CALCULATE BOOST DAYS
# ==============================

def get_boost_days(member: discord.Member) -> int:
    """Tính toán số ngày boost chính xác. Đảm bảo tính nhất quán cho Engine."""
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    # Sử dụng hiệu số thời gian thực tế để tránh sai lệch khi Render restart
    diff = now - member.premium_since
    return max(0, diff.days)


# ==============================
# GET ALL BOOSTER SYSTEM ROLES (IDs Only)
# ==============================

def get_system_role_ids(booster_role_id: any, levels: list) -> set:
    """
    Cung cấp danh sách ID cho Radar quét 2 chiều.
    Hỗ trợ Radar tự động tìm người boost và thu hồi role lậu.
    """
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
    """Tự động dọn dẹp cấu hình nếu Admin lỡ tay xóa Role trong Settings Server"""
    changed = False
    new_levels = []

    for lvl in levels:
        role_id = lvl.get("role")
        if not role_id:
            changed = True
            continue

        role = guild.get_role(int(role_id))
        if not role:
            changed = True
            continue

        new_levels.append(lvl)

    return new_levels, changed


# ==============================
# VALIDATE LEVEL CONFIG (LOGIC CHỐT)
# ==============================

def validate_levels(levels: list, booster_role_id: any):
    """
    Kiểm tra logic hệ thống:
    - Mục 2: Level 1 mặc định 0 ngày.
    - Mục 22: Ngày phải tăng dần qua các Level.
    - Mục 23: Không được trùng Role giữa các mốc.
    """
    if not levels:
        return True, None

    role_set = set()
    if booster_role_id:
        role_set.add(str(booster_role_id))

    prev_days = -1

    for i, lvl in enumerate(levels):
        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            return False, f"Level {i+1} đang bị trống thông tin."

        r_id_str = str(role_id)

        # Kiểm tra Level 1 (Nền tảng)
        if i == 0:
            if int(days) != 0:
                return False, "Level 1 (Booster Role) bắt buộc phải là 0 ngày."
        else:
            # Kiểm tra tính tăng dần (Mục 22)
            if int(days) <= prev_days:
                return False, f"Cấp {i+1} ({days} ngày) không thể thấp hơn cấp trước ({prev_days} ngày)."

        # Kiểm tra trùng Role (Mục 23)
        if i > 0 and r_id_str == str(booster_role_id):
            return False, f"Role của Level {i+1} không được là Booster Role gốc."
            
        if i > 0 and r_id_str in role_set:
            return False, f"Role ở Level {i+1} đã bị trùng với mốc khác."

        role_set.add(r_id_str)
        prev_days = int(days)

    return True, None


# ==============================
# REORDER LEVELS (Atomic Move)
# ==============================

def move_level_up(levels: list, index: int):
    """Di chuyển Level lên trên (Giữ nguyên mốc 1)"""
    if index <= 1: return levels
    levels[index - 1], levels[index] = levels[index], levels[index - 1]
    return levels


def move_level_down(levels: list, index: int):
    """Di chuyển Level xuống dưới"""
    if index == 0 or index >= len(levels) - 1: return levels
    levels[index + 1], levels[index] = levels[index], levels[index + 1]
    return levels


# ==============================
# FORMATTING UI (ĐỒNG BỘ EMBED)
# ==============================

def format_level_status(lvl_idx: int, lvl_data: dict, guild: discord.Guild = None):
    """
    Tạo UI hiển thị cho Admin. 
    Đã đồng bộ để hiển thị trạng thái Embed từ hệ thống Greet/Leave.
    """
    role_id = lvl_data.get("role")
    days = lvl_data.get("days", 0)
    
    # Lấy thông tin Embed đang gán cho hệ thống Level từ Greet Storage
    embed_info = ""
    if guild:
        config = get_section(guild.id, "booster_level")
        embed_name = config.get("embed")
        if embed_name:
            embed_info = f"\n🎁 Embed: `{embed_name}`"
        else:
            embed_info = f"\n⚠️ *Chưa gán Embed chúc mừng*"

    if not role_id:
        role_status = "❌ Chưa thiết lập"
    else:
        if guild:
            role = guild.get_role(int(role_id))
            role_status = role.mention if role else f"ID: `{role_id}` (Lỗi)"
        else:
            role_status = f"<@&{role_id}>"
            
    return f"**Level {lvl_idx + 1}**\nRole: {role_status}\nDays: `{days}`{embed_info}"
