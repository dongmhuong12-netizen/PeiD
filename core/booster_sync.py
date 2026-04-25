import asyncio
import discord
from .booster_engine import assign_correct_level
from .booster_storage import get_guild_config
from .boost_utils import get_system_role_ids

# Bảo vệ API: Chỉ cho phép xử lý tối đa 10 người cùng lúc trên toàn cầu
MAX_CONCURRENT_SYNC = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNC)

# ==============================
# SYNC ONE MEMBER (Atomic Unit)
# ==============================

async def sync_member(member: discord.Member):
    """
    Đồng bộ Role cho 1 thành viên. 
    Gọi thẳng vào Engine để thực hiện quy tắc 1 User / 1 Role.
    """
    if member.bot: return
    
    async with semaphore:
        try:
            # Engine sẽ tự động check mốc ngày và gán đúng 1 Role (Gốc hoặc Level)
            await assign_correct_level(member)
        except Exception:
            pass # Giữ log sạch trên Render

# ==============================
# SYNC ONE GUILD (Smart Radar)
# ==============================

async def sync_guild(guild: discord.Guild):
    """
    Quét thông minh: Chỉ nhắm vào những người có khả năng liên quan.
    """
    # 1. Lấy danh sách Booster thực tế (VIP List từ Discord)
    boosters = set(guild.premium_subscribers)
    
    # 2. Lấy danh sách ID Role hệ thống (Gốc + Tất cả các Level)
    config = await get_guild_config(guild.id)
    system_role_ids = get_system_role_ids(config.get("booster_role"), config.get("levels", []))
    
    # 3. TỐI ƯU: Chỉ tìm những người ĐANG GIỮ Role hệ thống
    # Thay vì duyệt guild.members (100k+), ta duyệt theo từng Role (vài chục người)
    members_with_roles = set()
    if system_role_ids:
        for r_id in system_role_ids:
            role_obj = guild.get_role(int(r_id))
            if role_obj:
                # Cộng dồn các member đang giữ role này vào tập hợp
                members_with_roles.update(role_obj.members)

    # Hợp nhất: (Người đang Boost thật) + (Người đang giữ Role nhưng có thể đã unboost)
    targets = boosters.union(members_with_roles)

    if not targets:
        return

    # Quét song song (Tận dụng sức mạnh đa luồng của asyncio)
    tasks = [sync_member(m) for m in targets]
    await asyncio.gather(*tasks)

# ==============================
# SYNC ALL GUILDS (Global Loop)
# ==============================

async def sync_all_guilds(bot):
    """Chu kỳ quét toàn bộ các server mà Bot tham gia"""
    for guild in bot.guilds:
        if guild.unavailable or not guild.me.guild_permissions.manage_roles:
            continue
        try:
            await sync_guild(guild)
            # Nghỉ 1 giây để "thở" giữa các server, tránh bị Discord nghi ngờ
            await asyncio.sleep(1)
        except:
            continue

# ==============================
# BOOSTER RADAR LOOP
# ==============================

async def daily_sync_loop(bot):
    """Vòng lặp Radar chạy ngầm"""
    await bot.wait_until_ready()
    await asyncio.sleep(30) # Chờ Bot ổn định hoàn toàn

    while not bot.is_closed():
        print(f"[RADAR] Bắt đầu quét hệ thống Booster...", flush=True)
        await sync_all_guilds(bot)
        print(f"[RADAR] Hoàn tất chu kỳ quét.", flush=True)
        
        # Quét mỗi 6 tiếng (Tiêu chuẩn tối ưu cho Bot lớn)
        await asyncio.sleep(21600)

# ==============================
# REALTIME EVENT (Đánh chặn tức thì)
# ==============================

async def handle_member_update(before: discord.Member, after: discord.Member):
    """Đảm bảo đồng bộ ngay khi trạng thái Premium thay đổi"""
    if after.bot: return

    # Nếu có biến động về việc nhấn nút Boost hoặc hết hạn
    if before.premium_since != after.premium_since:
        # Gọi Engine để xử lý gán/gỡ và gửi Embed chúc mừng (nếu có)
        await sync_member(after)
