import discord
from discord.ext import commands
import asyncio
import os
from aiohttp import web

from core.state import State
from core.cache_manager import force_flush # Chốt chặn trí nhớ cuối cùng

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
    await asyncio.Event().wait()

# =========================
# BOT SETUP
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
    help_command=None 
)

# =========================
# EXTENSIONS (QUY HOẠCH CHIẾN LƯỢC)
# =========================

EXTENSIONS = [
    "core.root",                 # XƯƠNG (Skeleton): Phải nạp đầu tiên để tạo lệnh /p
    "commands.embed.embed_group", # THỊT (Logic): Chứa toàn bộ Create, Edit, Show, Delete
    "core.greet_leave",          
    "core.wellcome",             
    "core.booster",              
    "systems.reaction_role",     
    # "commands.embed.create" -> ĐÃ LOẠI BỎ: Để tránh xung đột nạp chồng lệnh
]

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            if ext in bot.extensions:
                await bot.reload_extension(ext)
            else:
                await bot.load_extension(ext)
            print(f"[LOAD] Success: {ext}", flush=True)
        except Exception as e:
            if "already loaded" in str(e).lower():
                print(f"[LOAD] Info: {ext} đã được nạp trước đó.", flush=True)
            else:
                print(f"[LOAD ERROR] {ext}: {e}", flush=True)

# =========================
# READY STATE
# =========================

bot._ready_once = False

@bot.event
async def on_ready():
    if bot._ready_once:
        return
    bot._ready_once = True

    # 1. TRÍ NHỚ BỀN VỮNG: Khôi phục trạng thái từ RAM/Disk
    try:
        await State.resync()
        print("[STATE] Trí nhớ bền vững đã được khôi phục!", flush=True)
    except Exception as e:
        print(f"[STATE ERROR] {e}", flush=True)

    # 2. SLASH SYNC: Ép đồng bộ cây lệnh hợp nhất lên Discord
    try:
        print("[SLASH] Đang đồng bộ hóa toàn bộ hệ thống lệnh...", flush=True)
        synced = await bot.tree.sync()
        print(f"[SLASH] ✅ Thành công! Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)

# =========================
# MAIN ENTRY
# =========================

async def main():
    # Bật X-quang soi lỗi mạng
    discord.utils.setup_logging()

    # Chạy Web Server ngầm
    asyncio.create_task(run_web_server())

    # Nạp các thành phần theo trình tự ưu tiên
    await load_extensions()

    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        force_flush()
        print("[EXIT] Bot đã tắt an toàn.")
