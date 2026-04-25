import discord
from discord.ext import commands
import asyncio
import os
import signal
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
    
    # Giữ cho Web Server sống ngầm mà không block luồng chính
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
# EXTENSIONS (ĐỒNG BỘ 100k+)
# =========================

EXTENSIONS = [
    "core.root",                 # Hệ thống gốc
    "core.greet_leave",          # Hệ tiếp tân chính
    "core.wellcome",             # Hệ tiếp tân phụ
    "core.booster",              # Hệ thống quà tặng Booster
    "systems.reaction_role",     # Hệ thống gán role tự động
    "commands.embed.embed_group", # Group lệnh /p embed
    "commands.embed.create",      # Lệnh /p embed create
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

    # 1. TRÍ NHỚ BỀN VỮNG: Khôi phục lại trạng thái cũ ngay khi tỉnh dậy
    # Đã khớp tên với core/state.py
    await State.resync()
    print("[STATE] Trí nhớ bền vững đã được khôi phục!", flush=True)

    # 2. SLASH SYNC: Đồng bộ lệnh với Discord
    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] ✅ Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)

# =========================
# SHUTDOWN PROTECTION
# =========================

async def shutdown(loop, signal=None):
    if signal:
        print(f"[SHUTDOWN] Nhận tín hiệu {signal.name}...", flush=True)
    
    print("[SHUTDOWN] Đang ép ghi cache xuống đĩa...", flush=True)
    force_flush() 
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

# =========================
# MAIN ENTRY
# =========================

async def main():
    # Bật logging để theo dõi kết nối Discord
    discord.utils.setup_logging()

    # Chạy Web Server ngầm
    asyncio.create_task(run_web_server())

    # Nạp các thành phần
    await load_extensions()

    # Khởi động Bot
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        force_flush()
        print("[EXIT] Bot đã tắt an toàn.")
