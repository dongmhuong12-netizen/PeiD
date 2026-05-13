import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.state import State
# [CẤY MỚI] Nạp lớp MongoDB để khởi động cỗ máy dữ liệu
from core.mongodb import MongoDB 

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

# [CẤY ID BOSS - KHÔNG THAY ĐỔI LOGIC CŨ]
bot.boss_id = 1055476307372294155

# [CẤY MỚI] Gắn bot vào State để các module Storage có thể gọi bot.db
State.bot = bot 

# =========================
# EXTENSIONS (QUY HOẠCH CHIẾN LƯỢC)
# =========================

EXTENSIONS = [
    "core.root",                  
    "systems.button_listener",     
    "commands.embed.embed_group",  
    "core.greet_leave",          
    "core.wellcome",             
    "core.booster",              
    "systems.reaction_role",     
    "commands.fun.yiyi_core",     
    "commands.embed.embed_advanced", 
    "commands.embed.embed_webhook",  
    "commands.embed.embed_link",     
    "commands.identity.identity_group",
    "commands.ticket.ticket_group",  
    "commands.forms.forms_group",    
]

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            if ext not in bot.extensions:
                await bot.load_extension(ext)
                print(f"[LOAD] Success: {ext}", flush=True)
            else:
                await bot.reload_extension(ext)
                print(f"[RELOAD] Success: {ext}", flush=True)
        except Exception as e:
            print(f"[LOAD ERROR] {ext}: {e}", flush=True)

# =========================
# SỰ KIỆN HỆ THỐNG
# =========================

@bot.event
async def on_member_join(member: discord.Member):
    pass

# =========================
# READY STATE
# =========================

bot._ready_once = False

@bot.event
async def on_ready():
    if bot._ready_once:
        return
    bot._ready_once = True

    # 1. SLASH SYNC
    try:
        print("[SLASH] Đang đồng bộ hóa cây lệnh hợp nhất...", flush=True)
        synced = await bot.tree.sync()
        print(f"[SLASH] ✅ Thành công! Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)
    print(f"👑 Đã nhận diện thực thể tối cao: {bot.boss_id}", flush=True)

# =========================
# MAIN ENTRY
# =========================

async def main():
    discord.utils.setup_logging()
    
    # [CẤY MỚI] Khởi tạo kết nối MongoDB trước khi nạp Cogs
    uri = os.getenv("MONGO_URI")
    if uri:
        bot.db = MongoDB(uri)
        await bot.db.connect()
        print("[DB] MongoDB Atlas đã kết nối thành công!", flush=True)
    else:
        print("[DB WARNING] Không tìm thấy MONGO_URI. Bot đang chạy chế độ RAM-Only!", flush=True)

    asyncio.create_task(run_web_server())
    await load_extensions()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("[EXIT] Bot đã tắt an toàn.")
