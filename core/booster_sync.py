import asyncio
import discord
from .booster_engine import assign_correct_level
from .booster_storage import get_guild_config
from .boost_utils import get_system_role_ids

# Giới hạn số lượng xử lý cùng lúc để bảo vệ API
MAX_CONCURRENT_SYNC = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNC)

# ==============================
# SYNC ONE MEMBER (Bọc an toàn)
# ==============================

async def sync_member(member: discord.Member):
    if member.bot:
        return
    
    async with semaphore:
        try:
            # Engine đã được tối ưu Atomic (Gán/Gỡ trong 1 nốt nhạc)
            await assign_correct_level(member)
        except Exception as e:
            pass # Giảm bớt log rác để tránh nặng file log trên Render

# ==============================
# SYNC ONE GUILD (Radar Quét Sạch)
# ==============================

async def sync_guild(guild: discord.Guild):
    # 1. Lấy danh sách Booster thực tế
    boosters = set(guild.premium_subscribers)
    
    # 2. Lấy danh sách những người đang giữ Role hệ thống (để thu hồi nếu họ unboost)
    config = await get_guild_config(guild.id)
    system_role_ids = get_system_role_ids(config.get("booster_role"), config.get("levels", []))
    
    # Tìm những người đang giữ role hệ thống
    members_with_roles = []
    if system_role_ids:
        for member in guild.members:
            # Kiểm tra xem member có giữ bất kỳ role nào trong hệ thống không
            has_role = any(str(r.id) in system_role_ids for r in member.roles)
            if has_role:
                members_with_roles.append(member)

    # Hợp nhất danh sách: Người đang boost + Người đang giữ role (để check unboost)
    targets = boosters.union(set(members_with_roles))

    if not targets:
        return

    # Quét song song để tăng tốc độ
    tasks = [sync_member(m) for m in targets]
    await asyncio.gather(*tasks)

# ==============================
# SYNC ALL GUILDS
# ==============================

async def sync_all_guilds(bot):
    for guild in bot.guilds:
        if guild.unavailable:
            continue
        try:
            await sync_guild(guild)
            # Nghỉ ngắn giữa các server để Discord không đánh dấu spam
            await asyncio.sleep(1)
        except:
            continue

# ==============================
# BOOSTER RADAR LOOP
# ==============================

async def daily_sync_loop(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(30) # Chờ bot ổn định sau startup

    while not bot.is_closed():
        print(f"[RADAR] Bắt đầu quét hệ thống Booster toàn server...", flush=True)
        await sync_all_guilds(bot)
        print(f"[RADAR] Hoàn tất chu kỳ quét.", flush=True)
        
        # Quét mỗi 6 tiếng (Tiêu chuẩn 100k+) thay vì 24 tiếng
        await asyncio.sleep(21600)

# ==============================
# REALTIME EVENT HANDLER
# ==============================

async def handle_member_update(before: discord.Member, after: discord.Member):
    """Xử lý ngay lập tức khi có người nhấn nút Boost hoặc Unboost"""
    if after.bot:
        return

    # Nếu trạng thái boost thay đổi (Bắt đầu boost hoặc hết hạn)
    if before.premium_since != after.premium_since:
        await sync_member(after)
