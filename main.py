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
    help_command=None # Thường Bot hiện đại dùng Slash thay vì Help text
)

# =========================
# EXTENSIONS (BẢN FULL ĐỒNG BỘ 100k+)
# =========================

EXTENSIONS = [
    "core.root",                 # Hệ thống gốc
    "core.greet_leave",          # Hệ tiếp tân chính
    "core.wellcome",             # Hệ tiếp tân phụ
    "core.booster",              # Hệ thống quà tặng Booster
    "systems.reaction_role",     # Hệ thống gán role tự động
    "commands.embed.embed_group", # Group lệnh /p embed
    "commands.embed.create",      # Lệnh /p embed create
    # "commands.voice_system",    # Tạm ẩn theo yêu cầu của Nguyệt
    # "core.voice_listener",      # Tạm ẩn theo yêu cầu của Nguyệt
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
            # Bắt lỗi "already loaded" từ discord.py hoặc ClientException từ Cog
            if "already loaded" in str(e).lower():
                print(f"[LOAD] Info: {ext} đã được nạp trước đó (Bỏ qua).", flush=True)
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
    await State.resync()
    print("[STATE] Trí nhớ bền vững đã được khôi phục!", flush=True)

    # 2. SLASH SYNC: Đồng bộ lệnh với Discord
    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)

# =========================
# SHUTDOWN PROTECTION (BẢO VỆ DỮ LIỆU)
# =========================

async def shutdown(loop, signal=None):
    """Đảm bảo ghi mọi dữ liệu vào đĩa trước khi app bị Render tắt"""
    if signal:
        print(f"[SHUTDOWN] Nhận tín hiệu {signal.name}...", flush=True)
    
    print("[SHUTDOWN] Đang ép ghi cache xuống đĩa...", flush=True)
    force_flush() # Ghi file .json cuối cùng
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

# =========================
# MAIN ENTRY
# =========================

async def main():
    # Khởi tạo các thành phần hỗ trợ
    # bot.voice_manager = VoiceManager(bot) # Tạm ẩn

    # TÁCH LUỒNG: Chạy Web Server ngầm bằng Event Loop, trả lại tài nguyên
    asyncio.create_task(run_web_server())

    await load_extensions()

    # Khởi động Bot an toàn với Context Manager
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Xử lý khi nhấn Ctrl+C
        force_flush()
        print("[EXIT] Bot đã tắt an toàn.")
