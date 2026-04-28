import discord
import asyncio
from collections import defaultdict # [VÁ LỖI]

# Import từ storage (Chỉ lấy config để check role gốc)
from .booster_storage import get_guild_config

# [VÁ LỖI] Khóa Guild để bảo toàn tính nhất quán, tránh tranh chấp khi gán/gỡ role
_engine_locks = defaultdict(asyncio.Lock)

# ==============================
# ASSIGN CORRECT ROLE (Atomic Sync)
# ==============================

async def assign_correct_level(member: discord.Member):
    """
    hàm cốt lõi: xử lý gán/gỡ booster role gốc.
    đã loại bỏ hoàn toàn hệ thống mốc level và tính toán ngày.
    """
    guild = member.guild
    
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
