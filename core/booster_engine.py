import discord
from datetime import datetime, timezone
import asyncio

# Import từ storage (Đảm bảo các hàm này là async)
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
# CLEAN INVALID LEVELS
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
    # Chỉ tính Level nếu số ngày boost > 0 (Tránh nhận nhầm người không boost)
    if boost_days < 0: return 0
    
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
    HÀM CỐT LÕI: Đã sửa lỗi không gỡ role cho người hết Boost.
    """
    guild = member.guild
    config = await get_guild_config(guild.id)
    if not config: return None

    bot_member = guild.me
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        return None

    # 1. Dọn dẹp dữ liệu và xác định trạng thái Boost thực tế
    config = await clean_invalid_levels(guild, config)
    levels = config.get("levels", [])
    
    # XÁC ĐỊNH: Họ có thực sự đang Boost không?
    # Nếu premium_since là None VÀ không phải đang giả lập ngày (>0), thì là KHÔNG BOOST.
    is_actually_boosting = (member.premium_since is not None) or (mock_days is not None and mock_days > 0)

    # 2. Lấy danh sách Role liên quan để quét sạch
    base_role_id = config.get("booster_role")
    base_role = guild.get_role(int(base_role_id)) if base_role_id else None

    all_booster_related_roles = []
    if base_role: all_booster_related_roles.append(base_role)
    for lvl in levels:
        r = guild.get_role(int(lvl["role"]))
        if r: all_booster_related_roles.append(r)

    # 3. Xác định Role Đích (Target)
    final_target_role = None
    target_lv = 0

    if is_actually_boosting:
        boost_days = mock_days if mock_days is not None else calculate_boost_days(member)
        target_lv = get_target_level(boost_days, levels)
        
        # Nếu đạt Level nào đó
        if target_lv > 0 and (target_lv - 1) < len(levels):
            final_target_role = guild.get_role(int(levels[target_lv-1]["role"]))
        else:
            # Nếu đang boost nhưng chưa đạt level nào thì giữ Role gốc
            final_target_role = base_role

    # Check Hierarchy: Bot không gán được role cao hơn nó
    if final_target_role and final_target_role >= bot_member.top_role:
        final_target_role = None

    # 4. THỰC THI ATOMIC (Gỡ sạch, giữ 1)
    new_roles = set(member.roles)
    changed = False
    gained_new_level = False

    # Gỡ sạch toàn bộ role booster nếu không phải role đích
    for r in all_booster_related_roles:
        if r in new_roles and r != final_target_role:
            if r < bot_member.top_role:
                new_roles.remove(r)
                changed = True

    # Cắm Role Đích (Nếu có)
    if final_target_role and final_target_role not in new_roles:
        new_roles.add(final_target_role)
        changed = True
        if target_lv > 0: gained_new_level = True

    # Chỉ gọi API nếu thực sự có biến động
    if changed:
        try:
            await member.edit(
                roles=list(new_roles), 
                reason=f"Booster Sync: Days {calculate_boost_days(member) if mock_days is None else mock_days} (Lv {target_lv})"
            )
            
            # Gửi tin nhắn thông báo (Phải có await)
            if gained_new_level:
                from core.greet_leave import send_config_message
                await send_config_message(guild, member, "booster_level")
                
        except Exception as e:
            print(f"[ENGINE ERROR] Fail to edit roles for {member.id}: {e}", flush=True)

    return target_lv
