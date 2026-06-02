#Core/booster_engine.py
import discord
import asyncio
import time # [QUAN TRỌNG] để check thời gian hết hạn test
from collections import defaultdict

# Import trí nhớ State để check bypass
from core.state import State
# Import từ storage
from core.booster_storage import get_guild_config # [SỬA LỖI ĐƯỜNG DẪN]

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
    # [GIA CỐ]: is_testing chỉ đúng khi còn state_data và chưa quá expiry
    is_testing = state_data is not None and time.time() < state_data.get("expiry", 0)

    # [VÁ LỖI] Khóa Guild để bảo vệ tiến trình thực thi duy nhất
    lock = _engine_locks[guild.id]
    async with lock:
        try:
            bot_member = guild.me
            if not bot_member or not bot_member.guild_permissions.manage_roles:
                print(f"[ENGINE FAIL] Yiyi bị tước quyền Manage Roles tại server {guild.name}!", flush=True)
                return

            # [TỐI ƯU]: Chỉ nạp Config nếu base_role chưa được truyền vào
            if base_role is None:
                config = await get_guild_config(guild.id)
                if not config: return
                # [SỬA LỖI BIẾN]: Hỗ trợ cả key cũ và mới để Dashboard ko bị hụt data
                base_role_id = config.get("booster_role") or config.get("role_id")
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
                        print(f"[ENGINE SUCCESS] Đã gán role {base_role.name} cho {member.name}", flush=True)
                    except discord.Forbidden:
                        print(f"[ENGINE 403] Không đủ quyền API để gán vai trò {base_role.name} cho {member.name}", flush=True)
                else:
                    # [X-RAY]: Ép vạch mặt lỗi phân cấp im lặng
                    print(f"[ENGINE ERROR] LỖI PHÂN CẤP: Role {base_role.name} nằm CAO HƠN role của Yiyi! Yiyi không thể gán.", flush=True)
                    
            elif not should_have_role and has_role:
                # [BẢO VỆ]: Tuyệt đối không gỡ nếu đang trong trạng thái testing
                if not is_testing:
                    # [RESTORE]: Khôi phục check phân cấp gốc
                    if base_role < bot_member.top_role:
                        try:
                            await member.remove_roles(base_role, reason="Booster Sync: Ended/Expired")
                            print(f"[ENGINE SUCCESS] Đã gỡ role của {member.name}", flush=True)
                        except discord.Forbidden:
                            print(f"[ENGINE 403] Không đủ quyền API để gỡ vai trò {base_role.name} của {member.name}", flush=True)
                    else:
                        # [X-RAY]: Ép vạch mặt lỗi phân cấp im lặng
                        print(f"[ENGINE ERROR] LỖI PHÂN CẤP: Role {base_role.name} nằm CAO HƠN role của Yiyi! Yiyi không thể gỡ.", flush=True)

        except Exception as e:
            # Chỉ in lỗi nếu thực sự nghiêm trọng để tránh spam log server 100k
            if not isinstance(e, discord.Forbidden):
                print(f"[engine error] fail to sync role for {member.id}: {e}", flush=True)
        finally:
            # [BẢO VỆ LOCK]: Không tự ý hủy tham chiếu Khóa khi các tác vụ dị bộ khác vẫn đang xếp hàng chờ thực thi trong Queue
            pass

# ==============================
# PROACTIVE FULL SYNC (Industrial Scan)
# ==============================

async def sync_all_boosters(guild: discord.Guild):
    """
    hàm truy quét: tự động tìm toàn bộ booster trong server để đồng bộ role `booster`.
    """
    print(f"--- [SYNC START] Bắt đầu quét Guild: {guild.name} ---", flush=True)
    
    # [FIX CHÍ MẠNG]: Đọc Config 1 lần duy nhất cho toàn server
    config = await get_guild_config(guild.id)
    if not config: 
        print("[SYNC SKIP] Bỏ qua: Không tìm thấy Config Booster trong DB.", flush=True)
        return
        
    # [SỬA LỖI BIẾN]: Đồng bộ key với Dashboard
    role_id = config.get("booster_role") or config.get("role_id")
    if not role_id: 
        print("[SYNC SKIP] Bỏ qua: Config có lấy được nhưng thiếu ID Role.", flush=True)
        return
    
    try:
        base_role = guild.get_role(int(role_id))
    except (ValueError, TypeError):
        return
    if not base_role: 
        print(f"[SYNC SKIP] Bỏ qua: Role ID {role_id} không tồn tại trên Server.", flush=True)
        return

    if not guild.me.guild_permissions.manage_roles:
        print("[SYNC SKIP] Bỏ qua: Yiyi không có quyền Manage Roles trên Server.", flush=True)
        return

    # [VÁ LỖI PHÂN PHỐI CACHE]: Cưỡng bức nạp gói dữ liệu thành viên để tránh bỏ sót danh sách khi Bot vừa reboot/mất bộ nhớ RAM tạm thời
    if not guild.chunked:
        try:
            await guild.chunk()
        except Exception as e:
            print(f"[SYNC CACHE WARNING] Lỗi ép nạp gói chunk: {e}", flush=True)

    # [CƠ CHẾ TÌM BOOSTER TỐI ƯU 100K+]: Trích xuất thủ công trên toàn bộ member, bỏ qua biến premium_subscribers để chống mù cache
    actual_boosters = {m for m in guild.members if m.premium_since is not None}
    role_holders = {m for m in guild.members if base_role in m.roles}
    target_members = actual_boosters.union(role_holders)

    print(f"[SYNC DEBUG] Radar quét thấy: {len(actual_boosters)} người boost thật, {len(role_holders)} người đang cầm role.", flush=True)

    if not target_members:
        print("[SYNC SKIP] Dữ liệu rỗng: Không có ai đang boost và cũng không có ai đang cầm role.", flush=True)
        return

    # [VÁ LỖI] Semaphore: Phân luồng 50 task/lần để bảo vệ RAM
    sem = asyncio.Semaphore(50)
    
    # Truyền thẳng base_role xuống để Engine không phải đọc lại JSON
    tasks = [assign_correct_level(member, semaphore=sem, base_role=base_role) for member in target_members if not member.bot]
    
    if tasks:
        # return_exceptions=True để 1 task lỗi không làm dừng toàn bộ tiến trình quét
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # X-RAY: Ép lộ diện các lỗi bị asyncio.gather nuốt ngầm
        for r in results:
            if isinstance(r, Exception):
                print(f"[SYNC GATHER ERROR] Lỗi đồng bộ ngầm bị nuốt: {r}", flush=True)
                
    print(f"--- [SYNC DONE] Kết thúc quét Guild: {guild.name} ---", flush=True)
