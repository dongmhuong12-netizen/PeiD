import discord
import asyncio
import time # [QUAN TRỌNG] để check thời gian hết hạn test
from collections import defaultdict

# Import trí nhớ State để check bypass
from core.state import State
# Import từ storage
from .booster_storage import get_guild_config

# [VÁ LỖI] Khóa Guild để bảo toàn tính nhất quán trong môi trường Multi-server
_engine_locks = defaultdict(asyncio.Lock)

# ==============================
# ASSIGN CORRECT ROLE (Atomic Sync)
# ==============================

async def assign_correct_level(member: discord.Member, semaphore: asyncio.Semaphore = None, base_role: discord.Role = None):
    """
    hàm cốt lõi: xử lý gán/gỡ booster role gốc.
    logic hội tụ: kiểm tra (boost thật) hoặc (đang trong thời gian test).
    """
    if semaphore:
        async with semaphore:
            return await _execute_assign_logic(member, base_role)
    return await _execute_assign_logic(member, base_role)

async def _execute_assign_logic(member: discord.Member, base_role: discord.Role = None):
    """Logic thực thi gán/gỡ tách biệt để đảm bảo atomic"""
    guild = member.guild
    
    # [FIX] Đã đồng bộ key với booster.py: thêm guild.id để tránh lệch pha bypass
    bypass_key = f"boost_test_{guild.id}_{member.id}"
    state_data = await State.get_ui(bypass_key)
    is_testing = state_data and time.time() < state_data.get("expiry", 0)

    # [VÁ LỖI] Khóa Guild để bảo vệ tiến trình thực thi duy nhất
    lock = _engine_locks[guild.id]
    async with lock:
        try:
            bot_member = guild.me
            if not bot_member or not bot_member.guild_permissions.manage_roles:
                return

            # [TỐI ƯU]: Chỉ nạp Config nếu base_role chưa được truyền vào
            if base_role is None:
                config = await get_guild_config(guild.id)
                if not config: return
                base_role_id = config.get("booster_role")
                if not base_role_id: return
                try:
                    base_role = guild.get_role(int(base_role_id))
                except (ValueError, TypeError):
                    return
                if not base_role: return

            # [LOGIC HỘI TỤ]: Phải có role nếu (boost thật) HOẶC (đang test)
            is_boosting_real = member.premium_since is not None
            should_have_role = is_boosting_real or is_testing
            has_role = base_role in member.roles

            # thực thi logic gán/gỡ atomic
            if should_have_role and not has_role:
                # [RESTORE & FIX]: Khôi phục check phân cấp gốc + bọc Try/Except bảo vệ API
                if base_role < bot_member.top_role:
                    try:
                        await member.add_roles(base_role, reason="Booster Sync: Active/Test")
                    except discord.Forbidden:
                        pass
                    
            elif not should_have_role and has_role:
                # [BẢO VỆ]: Tuyệt đối không gỡ nếu đang trong trạng thái testing
                if not is_testing:
                    # [RESTORE]: Khôi phục check phân cấp gốc
                    if base_role < bot_member.top_role:
                        try:
                            await member.remove_roles(base_role, reason="Booster Sync: Ended/Expired")
                        except discord.Forbidden:
                            pass

        except Exception as e:
            # Chỉ in lỗi nếu thực sự nghiêm trọng để tránh spam log server 100k
            if not isinstance(e, discord.Forbidden):
                print(f"[engine error] fail to sync role for {member.id}: {e}", flush=True)
        finally:
            # [VÁ LỖI] Giải phóng RAM Lock
            if guild.id in _engine_locks and not lock.locked():
                _engine_locks.pop(guild.id, None)

# ==============================
# PROACTIVE FULL SYNC (Industrial Scan)
# ==============================

async def sync_all_boosters(guild: discord.Guild):
    """
    hàm truy quét: tự động tìm toàn bộ booster trong server để đồng bộ role `booster`.
    """
    # [FIX CHÍ MẠNG]: Đọc Config 1 lần duy nhất cho toàn server
    config = await get_guild_config(guild.id)
    if not config: return
    role_id = config.get("booster_role")
    if not role_id: return
    
    try:
        base_role = guild.get_role(int(role_id))
    except (ValueError, TypeError):
        return
    if not base_role: return

    if not guild.me.guild_permissions.manage_roles:
        return

    # [CƠ CHẾ TÌM BOOSTER TỐI ƯU 100K+]: Chỉ gom những người liên quan (O(1) thay vì O(N))
    actual_boosters = set(guild.premium_subscribers)
    role_holders = set(base_role.members)
    target_members = actual_boosters.union(role_holders)

    if not target_members:
        return

    # [VÁ LỖI] Semaphore: Phân luồng 50 task/lần để bảo vệ RAM
    sem = asyncio.Semaphore(50)
    
    # Truyền thẳng base_role xuống để Engine không phải đọc lại JSON
    tasks = [assign_correct_level(member, semaphore=sem, base_role=base_role) for member in target_members if not member.bot]
    
    if tasks:
        # return_exceptions=True để 1 task lỗi không làm dừng toàn bộ tiến trình quét
        await asyncio.gather(*tasks, return_exceptions=True)
