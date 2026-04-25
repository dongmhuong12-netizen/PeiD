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
    diff = now - member.premium_since
    return max(0, diff.days)

# ==============================
# CLEAN INVALID LEVELS (Tối ưu I/O)
# ==============================

async def clean_invalid_levels(guild: discord.Guild, config: dict):
    levels = config.get("levels", [])
    if not levels: return config
    new_levels = []
    changed = False
    for lvl in levels:
        role = guild.get_role(int(lvl.get("role")))
        if role: new_levels.append(lvl)
        else: changed = True
    if changed:
        config["levels"] = new_levels
        await save_guild_config(guild.id, config)
    return config

# ==============================
# GET TARGET LEVEL
# ==============================

def get_target_level(boost_days: int, levels: list):
    if not levels: return 0
    target_idx = -1
    for index, lvl in enumerate(levels):
        if boost_days >= lvl.get("days", 0):
            target_idx = index
        else: break
    return target_idx + 1

# ==============================
# ASSIGN CORRECT LEVEL (Atomic Sync)
# ==============================

async def assign_correct_level(member: discord.Member, mock_days: int = None):
    """
    HÀM CỐT LÕI: Đã sửa lỗi không tìm thấy người gán Role gốc.
    Đảm bảo quy tắc: 1 User / 1 Role (Gốc hoặc Level).
    """
    guild = member.guild
    config = await get_guild_config(guild.id)
    if not config: return None

    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        return None

    # 1. Dọn dẹp dữ liệu
    config = await clean_invalid_levels(guild, config)
    levels = config.get("levels", [])
    
    # Lấy đối tượng Role gốc (Booster Role)
    base_role_id = config.get("booster_role")
    base_role = guild.get_role(int(base_role_id)) if base_role_id else None

    # 2. Thu thập "Tập hợp Role Booster" để xử lý gỡ sạch
    all_booster_related_roles = []
    if base_role: all_booster_related_roles.append(base_role)
    for lvl in levels:
        r = guild.get_role(int(lvl["role"]))
        if r: all_booster_related_roles.append(r)

    # 3. Xác định Role Đích (Target)
    boost_days = mock_days if mock_days is not None else calculate_boost_days(member)
    target_lv = get_target_level(boost_days, levels)
    
    final_target_role = None
    if boost_days > 0 or mock_days is not None:
        # Nếu đạt Level nào đó thì lấy Role Level, nếu không thì lấy Role gốc
        if target_lv > 0 and (target_lv - 1) < len(levels):
            # Tìm lại đối tượng role level từ ID trong levels
            final_target_role = guild.get_role(int(levels[target_lv-1]["role"]))
        else:
            final_target_role = base_role

    # Check Hierarchy (Bot không gán được role cao hơn nó)
    if final_target_role and final_target_role >= bot_member.top_role:
        final_target_role = None

    # 4. THỰC THI ATOMIC (Gỡ sạch đám cũ, cắm duy nhất 1 cái mới)
    new_roles = set(member.roles)
    changed = False
    gained_new_level = False

    # Gỡ TẤT CẢ các role liên quan đến Boost (bao gồm cả role gốc và các level khác)
    for r in all_booster_related_roles:
        if r in new_roles and r != final_target_role:
            if r < bot_member.top_role:
                new_roles.remove(r)
                changed = True

    # Cắm duy nhất 1 Role Đích
    if final_target_role and final_target_role not in new_roles:
        new_roles.add(final_target_role)
        changed = True
        # Chỉ đánh dấu Level Up nếu role đó thuộc danh sách Level (target_lv > 0)
        if target_lv > 0: gained_new_level = True

    # Chỉ gọi API nếu thực sự có biến động
    if changed:
        try:
            await member.edit(
                roles=list(new_roles), 
                reason=f"Booster Sync: Days {boost_days} (Lv {target_lv})"
            )
            
            if gained_new_level:
                from core.greet_leave import send_config_message
                await send_config_message(guild, member, "booster_level")
                
        except Exception: pass

    return target_lv
