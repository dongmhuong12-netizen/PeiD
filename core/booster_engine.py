import discord
from datetime import datetime, timezone
from .booster_storage import get_guild_config, save_guild_config

# ==============================
# CALCULATE BOOST DAYS
# ==============================

def calculate_boost_days(member: discord.Member):
    """Tính toán số ngày đã Boost dựa trên premium_since"""
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    # Dùng tổng giây để tính ngày chính xác tuyệt đối
    diff = now - member.premium_since
    return max(0, diff.days)


# ==============================
# CLEAN INVALID LEVELS (Tối ưu I/O)
# ==============================

async def clean_invalid_levels(guild: discord.Guild, config: dict):
    """Loại bỏ các Level có Role không còn tồn tại trong Server"""
    levels = config.get("levels", [])
    if not levels:
        return config

    new_levels = []
    changed = False

    for lvl in levels:
        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            changed = True
            continue

        role = guild.get_role(int(role_id))
        if not role:
            changed = True
            continue

        new_levels.append(lvl)

    if changed:
        config["levels"] = new_levels
        # Chỉ save khi thực sự có sự thay đổi để bảo vệ Disk I/O
        await save_guild_config(guild.id, config)

    return config


# ==============================
# GET TARGET LEVEL (Logic chuẩn 100k+)
# ==============================

def get_target_level(boost_days: int, levels: list):
    """Tìm level cao nhất mà user đạt điều kiện (Dựa trên danh sách đã sắp xếp)"""
    if not levels:
        return 0

    target_idx = -1
    for index, lvl in enumerate(levels):
        if boost_days >= lvl.get("days", 0):
            target_idx = index
        else:
            # Tối ưu CPU: Nếu ngày yêu cầu lớn hơn ngày thực tế, dừng quét ngay
            break

    return target_idx + 1 # Trả về 1-based index


# ==============================
# ASSIGN CORRECT LEVEL (Atomic Update)
# ==============================

async def assign_correct_level(member: discord.Member, mock_days: int = None):
    """
    HÀM CHỦ CHỐT: Gán role level và gửi thông báo.
    Giữ nguyên logic gộp Role (Atomic Edit) của Nguyệt.
    """
    guild = member.guild
    config = await get_guild_config(guild.id)
    if not config:
        return None

    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        return None

    # 1. Dọn dẹp dữ liệu rác
    config = await clean_invalid_levels(guild, config)
    levels = config.get("levels", [])

    # 2. Lấy danh sách đối tượng Role liên quan
    booster_role_objs = []
    for lvl in levels:
        r = guild.get_role(int(lvl["role"]))
        if r: booster_role_objs.append(r)

    # 3. Tính toán mục tiêu (Hỗ trợ Mock Days để Test)
    boost_days = mock_days if mock_days is not None else calculate_boost_days(member)
    target_lv = get_target_level(boost_days, levels)
    
    # Xác định role level cần phải có
    target_role = None
    if target_lv > 0 and (target_lv - 1) < len(booster_role_objs):
        target_role = booster_role_objs[target_lv - 1]

    # Kiểm tra quyền hạn Bot (Hierachy Check)
    if target_role and target_role >= bot_member.top_role:
        target_role = None

    # 4. THỰC THI ATOMIC EDIT (Gỡ cũ, Gán mới trong 1 Request duy nhất)
    old_roles = set(member.roles)
    new_roles = set(member.roles)
    changed = False
    gained_new_level = False

    # Loại bỏ các level role cũ không còn phù hợp
    for r in booster_role_objs:
        if r in new_roles and r != target_role:
            if r < bot_member.top_role:
                new_roles.remove(r)
                changed = True

    # Thêm level role mới đúng điều kiện
    if target_role and target_role not in new_roles:
        new_roles.add(target_role)
        changed = True
        gained_new_level = True # Đánh dấu để gửi thông báo

    # Chỉ gọi API nếu có thay đổi thực sự
    if changed:
        try:
            await member.edit(
                roles=list(new_roles), 
                reason=f"Booster Sync: {boost_days} days (Lv {target_lv})"
            )
            
            # --- MẠCH THÔNG BÁO LEVEL UP (ĐỒNG BỘ HỆ THỐNG) ---
            if gained_new_level and target_lv > 0:
                # Chỉ gửi khi thành viên thực sự được thăng cấp (không phải gỡ role)
                from core.greet_leave import send_config_message
                await send_config_message(guild, member, "booster_level")
                
        except discord.Forbidden:
            print(f"[ENGINE] Thiếu quyền quản lý role tại server {guild.id}", flush=True)
        except Exception as e:
            print(f"[ENGINE ERROR] {e}", flush=True)

    return target_lv
