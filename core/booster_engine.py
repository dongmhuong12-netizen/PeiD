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

async def assign_correct_level(member: discord.Member):
    """
    hàm cốt lõi: xử lý gán/gỡ booster role gốc.
    logic hội tụ: kiểm tra (boost thật) hoặc (đang trong thời gian test).
    """
    guild = member.guild
    
    # [1] KIỂM TRA TRẠNG THÁI TEST (VIRTUAL BOOST)
    # kiểm tra xem người dùng có đang được "miễn tử" bởi lệnh test không
    bypass_key = f"boost_test_{member.id}"
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

            base_role = guild.get_role(int(base_role_id))
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
                # kiểm tra hierarchy trước khi gỡ
                if base_role < bot_member.top_role:
                    await member.remove_roles(base_role, reason="Booster Sync: Ended/Expired")

        except Exception as e:
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
    được gọi khi setup role hoặc chạy chu kỳ quét định kỳ của bot.
    """
    # Lấy toàn bộ member (loại bỏ bot) để chuẩn bị đồng bộ
    # Với server 100k+, asyncio.gather xử lý task dựa trên event loop để tối ưu RAM
    tasks = [assign_correct_level(member) for member in guild.members if not member.bot]
    
    if tasks:
        await asyncio.gather(*tasks)
