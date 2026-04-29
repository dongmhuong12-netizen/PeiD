import discord
import asyncio
import time
from collections import defaultdict
from core.state import State
from .booster_storage import get_guild_config

# [VÁ LỖI] Khóa Guild để bảo toàn tính nhất quán trong môi trường Multi-server
_engine_locks = defaultdict(asyncio.Lock)

async def assign_correct_level(member: discord.Member):
    """
    Hàm cốt lõi (Atomic Sync): xử lý gán/gỡ role booster.
    Logic hội tụ: Kiểm tra (Boost thật) hoặc (Đang trong thời gian Test).
    """
    guild = member.guild
    
    # [1] KIỂM TRA TRẠNG THÁI TEST (VIRTUAL BOOST)
    bypass_key = f"boost_test_{member.id}"
    state_data = await State.get_ui(bypass_key)
    is_testing = state_data and time.time() < state_data.get("expiry", 0)

    # [VÁ LỖI] Khóa Guild để bảo vệ tiến trình thực thi, tránh Race Condition
    lock = _engine_locks[guild.id]
    async with lock:
        try:
            config = await get_guild_config(guild.id)
            if not config: return

            bot_member = guild.me
            if not bot_member or not bot_member.guild_permissions.manage_roles:
                return

            base_role_id = config.get("booster_role")
            if not base_role_id: return

            base_role = guild.get_role(int(base_role_id))
            if not base_role or base_role >= bot_member.top_role:
                return

            # [LOGIC HỘI TỤ]: Phải có role nếu (Boost thật) HOẶC (Đang test)
            is_boosting_real = member.premium_since is not None
            should_have_role = is_boosting_real or is_testing
            has_role = base_role in member.roles

            if should_have_role and not has_role:
                await member.add_roles(base_role, reason="Booster Sync: Active/Test")
            elif not should_have_role and has_role:
                await member.remove_roles(base_role, reason="Booster Sync: Ended/Expired")

        except Exception as e:
            print(f"[engine error] fail to sync role for {member.id}: {e}", flush=True)
        finally:
            if guild.id in _engine_locks and not lock.locked():
                _engine_locks.pop(guild.id, None)

async def sync_all_boosters(guild: discord.Guild):
    """
    Truy quét chủ động (Industrial Scan): Tự tìm toàn bộ booster trong server.
    Sử dụng gather để tối ưu hóa xử lý cho server 100k+ member.
    """
    tasks = [assign_correct_level(member) for member in guild.members if not member.bot]
    if tasks:
        await asyncio.gather(*tasks)
