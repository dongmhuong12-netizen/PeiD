import discord
import asyncio
import time # [QUAN TRỌNG] để check thời gian hết hạn test
from collections import defaultdict

# Import trí nhớ State để check bypass
from core.state import State
# Import từ storage
from .booster_storage import get_guild_config

# [VÁ LỖI] Khóa Guild để bảo toàn tính nhất quán
_engine_locks = defaultdict(asyncio.Lock)

# ==============================
# ASSIGN CORRECT ROLE (Atomic Sync)
# ==============================

async def assign_correct_level(member: discord.Member):
    """
    hàm cốt lõi: xử lý gán/gỡ booster role gốc.
    đã tích hợp chốt chặn bypass 5 phút để bảo vệ người test.
    """
    guild = member.guild
    
    # [BẢO VỆ 1] KIỂM TRA TRẠNG THÁI TEST (BYPASS)
    # tớ check ngay từ đầu để tránh tốn tài nguyên chạy lock
    bypass_key = f"boost_test_{member.id}"
    state_data = await State.get_ui(bypass_key)
    if state_data and time.time() < state_data.get("expiry", 0):
        # nếu đang trong thời gian test, dừng mọi hoạt động gỡ role
        return

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

            base_role = guild.get_role(int(base_role_id))
            if not base_role: return

            # xác định trạng thái boost thực tế từ discord
            is_boosting = member.premium_since is not None
            has_role = base_role in member.roles

            # thực thi logic gán/gỡ atomic
            if is_boosting and not has_role:
                # kiểm tra hierarchy trước khi gán
                if base_role < bot_member.top_role:
                    await member.add_roles(base_role, reason="Booster Sync: Active")
                    
            elif not is_boosting and has_role:
                # kiểm tra hierarchy trước khi gỡ
                if base_role < bot_member.top_role:
                    await member.remove_roles(base_role, reason="Booster Sync: Ended")

        except Exception as e:
            print(f"[engine error] fail to sync role for {member.id}: {e}", flush=True)
        finally:
            # [VÁ LỖI] Giải phóng RAM Lock
            if guild.id in _engine_locks and not lock.locked():
                _engine_locks.pop(guild.id, None)
