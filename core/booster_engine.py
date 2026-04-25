# ==============================
# ASSIGN CORRECT LEVEL (Atomic Update)
# ==============================

async def assign_correct_level(member: discord.Member, mock_days: int = None):
    guild = member.guild
    config = await get_guild_config(guild.id)
    if not config:
        return None

    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        return None

    # 1. Dọn dẹp dữ liệu rác (nếu có)
    config = await clean_invalid_levels(guild, config)
    levels = config.get("levels", [])

    # 2. Lấy danh sách tất cả role liên quan đến hệ thống level
    booster_role_objs = []
    for lvl in levels:
        r = guild.get_role(int(lvl["role"]))
        if r: booster_role_objs.append(r)

    # 3. Tính toán mục tiêu
    # NẾU CÓ MOCK_DAYS THÌ ƯU TIÊN SỬ DỤNG ĐỂ TEST, NẾU KHÔNG THÌ LẤY NGÀY THỰC TẾ
    boost_days = mock_days if mock_days is not None else calculate_boost_days(member)
    target_lv = get_target_level(boost_days, levels)
    
    # Xác định role cần có
    target_role = None
    if target_lv > 0 and (target_lv - 1) < len(booster_role_objs):
        target_role = booster_role_objs[target_lv - 1]

    # Kiểm tra quyền hạn của Bot đối với target_role
    import discord
from datetime import datetime, timezone
from .booster_storage import get_guild_config, save_guild_config

# ==============================
# CALCULATE BOOST DAYS
# ==============================

def calculate_boost_days(member: discord.Member):
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    # Dùng tổng giây để tính ngày chính xác hơn
    diff = now - member.premium_since
    return max(0, diff.days)


# ==============================
# CLEAN INVALID LEVELS (Tối ưu I/O)
# ==============================

async def clean_invalid_levels(guild: discord.Guild, config: dict):
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
        # Chỉ save khi thực sự có sự thay đổi (Tiết kiệm I/O)
        await save_guild_config(guild.id, config)

    return config


# ==============================
# GET TARGET LEVEL (Logic chuẩn 100k+)
# ==============================

def get_target_level(boost_days: int, levels: list):
    """Tìm level cao nhất mà user đạt điều kiện dựa trên danh sách đã sắp xếp"""
    if not levels:
        return 0

    target_idx = -1
    for index, lvl in enumerate(levels):
        if boost_days >= lvl.get("days", 0):
            target_idx = index
        else:
            # Vì danh sách đã được sắp xếp ở Storage, 
            # nếu gặp ngày lớn hơn boost_days thì dừng luôn (Tối ưu CPU)
            break

    return target_idx + 1 # Trả về 1-based index


# ==============================
# ASSIGN CORRECT LEVEL (Atomic Update)
# ==============================

async def assign_correct_level(member: discord.Member, mock_days: int = None):
    guild = member.guild
    config = await get_guild_config(guild.id)
    if not config:
        return None

    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        return None

    # 1. Dọn dẹp dữ liệu rác (nếu có)
    config = await clean_invalid_levels(guild, config)
    levels = config.get("levels", [])

    # 2. Lấy danh sách tất cả role liên quan đến hệ thống level
    booster_role_objs = []
    for lvl in levels:
        r = guild.get_role(int(lvl["role"]))
        if r: booster_role_objs.append(r)

    # 3. Tính toán mục tiêu
    # Ưu tiên mock_days nếu đang giả lập, ngược lại tính ngày thực tế
    boost_days = mock_days if mock_days is not None else calculate_boost_days(member)
    target_lv = get_target_level(boost_days, levels)
    
    # Xác định role cần có
    target_role = None
    if target_lv > 0 and (target_lv - 1) < len(booster_role_objs):
        target_role = booster_role_objs[target_lv - 1]

    # Kiểm tra quyền hạn của Bot đối với target_role
    if target_role and target_role >= bot_member.top_role:
        target_role = None

    # 4. THỰC THI ATOMIC EDIT (Gỡ và Gán trong 1 request)
    current_roles = set(member.roles)
    new_roles = set(member.roles)
    changed = False

    # Loại bỏ các level role không phù hợp
    for r in booster_role_objs:
        if r in new_roles and r != target_role:
            if r < bot_member.top_role:
                new_roles.remove(r)
                changed = True

    # Thêm level role đúng
    if target_role and target_role not in new_roles:
        new_roles.add(target_role)
        changed = True

    # Chỉ gọi API nếu thực sự có thay đổi (Tiết kiệm API tối đa)
    if changed:
        try:
            await member.edit(roles=list(new_roles), reason=f"Booster Sync: Day {boost_days} (Lv {target_lv})")
        except discord.Forbidden:
            pass
        except Exception:
            pass

    return target_lv
