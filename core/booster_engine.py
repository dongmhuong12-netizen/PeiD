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

async def assign_correct_level(member: discord.Member, semaphore: asyncio.Semaphore = None):
    """
    hàm cốt lõi: xử lý gán/gỡ booster role gốc.
    logic hội tụ: kiểm tra (boost thật) hoặc (đang trong thời gian test).
    """
    # [VÁ LỖI] Sử dụng Semaphore nếu được truyền vào để kiểm soát lưu lượng trên server 100k+
    if semaphore:
        async with semaphore:
            return await _execute_assign_logic(member)
    return await _execute_assign_logic(member)

async def _execute_assign_logic(member: discord.Member):
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
            config = await get_guild_config(guild.id)
            if not config: return

            bot_member = guild.me
            if not bot_member or not bot_member.guild_permissions.manage_roles:
                return

            # lấy booster role gốc từ cấu hình
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
                # kiểm tra hierarchy trước khi gán
                if base_role < bot_member.top_role:
                    await member.add_roles(base_role, reason="Booster Sync: Active/Test")
                    
            elif not should_have_role and has_role:
                # [BẢO VỆ]: Tuyệt đối không gỡ nếu đang trong trạng thái testing
                if not is_testing:
                    # kiểm tra hierarchy trước khi gỡ
                    if base_role < bot_member.top_role:
                        await member.remove_roles(base_role, reason="Booster Sync: Ended/Expired")

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
    # [VÁ LỖI] Semaphore: Chỉ cho phép xử lý 50 member cùng lúc để bảo vệ RAM và tránh Rate Limit
    # Với server 100k+, quăng 100k task vào gather cùng lúc sẽ làm sập bot.
    sem = asyncio.Semaphore(50)
    
    tasks = [assign_correct_level(member, semaphore=sem) for member in guild.members if not member.bot]
    
    if tasks:
        # return_exceptions=True để 1 task lỗi không làm dừng toàn bộ tiến trình quét
        await asyncio.gather(*tasks, return_exceptions=True)
