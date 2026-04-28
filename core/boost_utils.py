import discord
from datetime import datetime, timezone
from core.greet_storage import get_section
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# ==============================
# CALCULATE BOOST DAYS
# ==============================

def get_boost_days(member: discord.Member) -> int:
    """tính toán số ngày boost chính xác. đảm bảo tính nhất quán cho engine."""
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    # sử dụng hiệu số thời gian thực tế để tránh sai lệch khi render restart
    diff = now - member.premium_since
    return max(0, diff.days)


# ==============================
# GET ALL BOOSTER SYSTEM ROLES (IDs Only)
# ==============================

def get_system_role_ids(booster_role_id: any, levels: list) -> set:
    """
    cung cấp danh sách id cho radar quét 2 chiều.
    hỗ trợ radar tự động tìm người boost và thu hồi role lậu.
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
    """tự động dọn dẹp cấu hình nếu admin lỡ tay xóa role trong settings server"""
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
    kiểm tra logic hệ thống:
    - mốc 1 bắt buộc 0 ngày.
    - ngày phải tăng dần qua các level.
    - không được trùng role giữa các mốc.
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
            return False, f"level {i+1} đang bị trống thông tin"

        r_id_str = str(role_id)

        # kiểm tra level 1 (nền tảng)
        if i == 0:
            if int(days) != 0:
                return False, "level 1 (booster role) bắt buộc phải là 0 ngày"
        else:
            # kiểm tra tính tăng dần
            if int(days) <= prev_days:
                return False, f"cấp {i+1} (`{days}` ngày) không thể thấp hơn cấp trước (`{prev_days}` ngày)"

        # kiểm tra trùng role với booster role gốc
        if i > 0 and r_id_str == str(booster_role_id):
            return False, f"role của level {i+1} không được là booster role gốc"
            
        # kiểm tra trùng role với các mốc khác trong kho set
        if i > 0 and r_id_str in role_set:
            return False, f"role ở level {i+1} đã bị trùng với mốc khác"

        role_set.add(r_id_str)
        prev_days = int(days)

    return True, None


# ==============================
# REORDER LEVELS (Atomic Move)
# ==============================

def move_level_up(levels: list, index: int):
    """di chuyển level lên trên (giữ nguyên mốc 1)"""
    if index <= 1: return levels
    levels[index - 1], levels[index] = levels[index], levels[index - 1]
    return levels


def move_level_down(levels: list, index: int):
    """di chuyển level xuống dưới"""
    if index == 0 or index >= len(levels) - 1: return levels
    levels[index + 1], levels[index] = levels[index], levels[index + 1]
    return levels


# ==============================
# FORMATTING UI (ĐỒNG BỘ EMBED)
# ==============================

def format_level_status(lvl_idx: int, lvl_data: dict, guild: discord.Guild = None):
    """tạo ui hiển thị cho admin quản lý các mốc booster."""
    role_id = lvl_data.get("role")
    days = lvl_data.get("days", 0)
    
    # lấy thông tin embed đang gán
    embed_info = ""
    if guild:
        config = get_section(guild.id, "booster_level")
        embed_name = config.get("embed")
        if embed_name:
            embed_info = f"\nembed: `{embed_name}`"
        else:
            embed_info = f"\n{Emojis.HOICHAM} chưa gán embed chúc mừng booster, hãy đảm bảo cậu setup đầy đủ cấu hình"

    if not role_id:
        role_status = "chưa thiết lập"
    else:
        if guild:
            role = guild.get_role(int(role_id))
            role_status = role.mention if role else f"id: `{role_id}` (lỗi)"
        else:
            role_status = f"<@&{role_id}>"
            
    return f"**level {lvl_idx + 1}**\nrole: {role_status}\ndays: `{days}`{embed_info}"
