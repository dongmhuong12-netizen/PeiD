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
    "commands.embed.embed_advanced", # ADVANCED: Hệ thống Export, Import, Clone
    "commands.embed.embed_webhook",  # WEBHOOK: Hệ thống giả danh gửi tin nhắn
    "commands.embed.embed_link",     
    "commands.ticket.ticket_group",  # PHASE 3: Hệ thống Ticket hỗ trợ
    "commands.forms.forms_group",    # PHASE 3: Hệ thống Biểu mẫu Modal
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
# SỰ KIỆN TƯƠNG TÁC (NÃO XỬ LÝ PHASE 3)
# =========================

@bot.event
async def on_member_join(member: discord.Member):
    """[SECURITY] Mạch Verify cũ đã được gỡ bỏ theo yêu cầu để đảm bảo an toàn"""
    pass

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """[NÃO XỬ LÝ NÚT BẤM] Phân luồng tín hiệu Ticket và Forms"""
    try:
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            
            # IT Pro: Import bên trong để tránh Circular Import
            # Mạch xử lý TICKET
            if custom_id.startswith("yiyi:ticket:"):
                from systems.ticket_system import handle_ticket_interaction
                await handle_ticket_interaction(interaction)
                return

            # Mạch xử lý FORMS
            elif custom_id.startswith("yiyi:forms:"):
                from systems.forms_system import handle_forms_interaction
                await handle_forms_interaction(interaction)
                return
                
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
        pass
    finally:
        # Chốt chặn cuối cùng để bảo vệ dữ liệu JSON
        force_flush()
        print("[EXIT] Bot đã tắt an toàn và đã lưu dữ liệu.")
