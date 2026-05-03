import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.state import State
from core.cache_manager import force_flush 

# Đảm bảo thư mục dữ liệu luôn tồn tại
os.makedirs("data", exist_ok=True)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not found")

# =========================
# WEB SERVER (RENDER KEEP ALIVE)
# =========================

async def health(request):
    return web.Response(text="PeiD Bot is online and healthy!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[WEB] Service started on port {port}", flush=True)
    # Giữ web server sống cùng bot
    await asyncio.Event().wait()

# =========================
# BOT SETUP (SHARDING FOR 100K+)
# =========================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True
intents.voice_states = True

bot = commands.AutoShardedBot(
    command_prefix=commands.when_mentioned,
    intents=intents,
    help_command=None,
    status=discord.Status.idle,
    activity=discord.CustomActivity(name="˚₊‧꒰ა yiyi iu ໒꒱ ‧₊˚")
)

# =========================
# EXTENSIONS (QUY HOẠCH CHIẾN LƯỢC)
# =========================

EXTENSIONS = [
    "core.root",                  # XƯƠNG: Tạo lệnh /p (Phải nạp đầu tiên)
    "commands.embed.embed_group",  # THỊT: Create, Edit, Show...
    "core.greet_leave",          
    "core.wellcome",             
    "core.booster",              
    "systems.reaction_role",     
    "commands.fun.yiyi_core",     # LỆNH FUN YIYI: Hệ thống tương tác cá nhân hóa
    "commands.embed.embed_advanced", # ADVANCED: Hệ thống Export, Import, Clone (Phase 1)
    "commands.embed.embed_webhook",  # WEBHOOK: Hệ thống giả danh gửi tin nhắn (Phase 2)
    "commands.embed.embed_buttons",
    "commands.verify.verify_group",  # [MẠCH AN NINH] Đã nạp hệ thống Double Counter (Phase 3)
]

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            # Chỉ nạp nếu chưa có trong bộ nhớ để tránh lỗi trùng lặp
            if ext not in bot.extensions:
                await bot.load_extension(ext)
                print(f"[LOAD] Success: {ext}", flush=True)
            else:
                await bot.reload_extension(ext)
                print(f"[RELOAD] Success: {ext}", flush=True)
        except Exception as e:
            print(f"[LOAD ERROR] {ext}: {e}", flush=True)

# =========================
# SỰ KIỆN AN NINH (DÂY THẦN KINH PHASE 3)
# =========================

@bot.event
async def on_member_join(member: discord.Member):
    """[TỰ ĐỘNG XÍCH CỔ] Tự động gán Role Chưa Veri khi mem mới vào server"""
    try:
        from core.cache_manager import get_raw
        db = get_raw("verify_configs")
        config = db.get(str(member.guild.id))
        
        # Nếu server có cài đặt an ninh và có set Role Unverified
        if config and config.get("unverified_role"):
            u_role = member.guild.get_role(int(config["unverified_role"]))
            if u_role:
                await member.add_roles(u_role, reason="Yiyi Security: Auto-assigned Unverified Role")
    except Exception as e:
        print(f"[SECURITY WARNING] Lỗi gán Role Unverified cho {member.id}: {e}", flush=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """[NÃO XỬ LÝ NÚT BẤM] Lắng nghe nút Verify và truyền cho đao phủ xử lý"""
    try:
        if interaction.type == discord.InteractionType.component:
            # IT Pro: Import bên trong sự kiện để tránh lỗi vòng lặp Import (Circular Import)
            from systems.verify_system import VerifySystem
            
            # Truyền tín hiệu cho Hệ thống An ninh. Nếu nó bắt được ID của nó, nó sẽ xử lý và trả về True
            if await VerifySystem.handle_interaction(interaction):
                return # Đã xử lý xong, ngắt luồng để khỏi vướng các event khác
                
    except Exception as e:
        print(f"[INTERACTION WARNING] {e}", flush=True)

# =========================
# READY STATE
# =========================

bot._ready_once = False

@bot.event
async def on_ready():
    if bot._ready_once:
        return
    bot._ready_once = True

    # 1. KHÔI PHỤC TRÍ NHỚ
    try:
        await State.resync()
        print("[STATE] Trí nhớ bền vững đã được khôi phục!", flush=True)
    except Exception as e:
        print(f"[STATE ERROR] {e}", flush=True)

    # 2. SLASH SYNC (Chốt hạ toàn bộ cây lệnh)
    try:
        print("[SLASH] Đang đồng bộ hóa cây lệnh hợp nhất...", flush=True)
        # Đồng bộ toàn cầu (Có thể mất vài phút để cập nhật hết 100k server)
        synced = await bot.tree.sync()
        print(f"[SLASH] ✅ Thành công! Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)

# =========================
# MAIN ENTRY
# =========================

async def main():
    # Bật logging để soi lỗi Async/Network
    discord.utils.setup_logging()

    # Chạy Web Server ngầm cho Render
    asyncio.create_task(run_web_server())

    # Nạp extensions theo trình tự
    await load_extensions()

    async with bot:
        # Bắt đầu vòng đời của Bot
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Bỏ qua để nhường luồng xử lý cuối cùng cho finally
        pass
    finally:
        # Chốt chặn cuối cùng để bảo vệ dữ liệu JSON
        force_flush()
        print("[EXIT] Bot đã tắt an toàn và đã lưu dữ liệu.")



