import discord
from discord.ext import commands, tasks # [CẤY MỚI] Thêm tasks từ discord.ext
import asyncio
import os
from aiohttp import web

# [FIX DỨT ĐIỂM] Đưa Emojis lên import đầu file để Task background truy cập được ở mức global
from utils.emojis import Emojis 
from core.state import State
# [CẤY MỚI] Nạp lớp MongoDB để khởi động cỗ máy dữ liệu
from core.mongodb import MongoDB 

# ==========================================
# [GIẢI PHÁP TỐI THƯỢNG] TỰ CẠY FILE .ENV, ĐÁ BAY DOTENV
# ==========================================
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')

_TOKEN = None
_MONGO_URI = None

# Tự động đọc file chay, bỏ qua mọi lỗi của PM2 hay hệ thống
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip() # Cắt bỏ mọi khoảng trắng hay ký tự lỗi rác
            if line.startswith("TOKEN="):
                _TOKEN = line.split("=", 1)[1].strip(' "\'')
            elif line.startswith("MONGO_URI="):
                _MONGO_URI = line.split("=", 1)[1].strip(' "\'')

# Bơm thẳng vào não hệ thống
if _TOKEN: os.environ["TOKEN"] = _TOKEN
if _MONGO_URI: os.environ["MONGO_URI"] = _MONGO_URI

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError(f"Vẫn không có TOKEN! Sếp hãy gõ lệnh 'cat .env' kiểm tra xem có đúng dòng 'TOKEN=...' chưa!")

# =========================
# WEB SERVER (RENDER KEEP ALIVE)
# =========================

async def health(request):
    return web.Response(text="PeiD Bot is online and healthy!")

# [FIX] Đổi thành start_web_server, bỏ asyncio.Event().wait() để tránh tạo Zombie Task
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[WEB] Service started on port {port}", flush=True)
    return runner

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
# Gán trực tiếp vào bot để các task gọi an toàn
bot.emojis_sys = Emojis 

# [CẤY MỚI] Gắn bot vào State để các module Storage có thể gọi bot.db
State.bot = bot 

# =========================
# [CẤY MỚI] HỆ THỐNG VÒNG LẶP STATUS CHIẾN LƯỢC
# =========================
bot.status_index = 0

# Rate limit API: 5 lần đổi / 60 giây / 1 Shard. Đặt 30s là chu kỳ "ngắn nhất & an toàn nhất"
@tasks.loop(seconds=30)
async def rotate_status():
    try:
        # Gọi qua bot để đảm bảo namespace luôn tồn tại
        emj = getattr(bot, "emojis_sys", Emojis)
        emoji_no = getattr(emj, "NO", None)
        emoji_htt = getattr(emj, "HTT", None)
        
        statuses = [
            ("˚₊‧꒰ა yiyi iu ໒꒱ ‧₊˚", None),
            ("vương dỹ nguyệt", emoji_no),
            ("vạn diệp  〆  ≋", emoji_htt)
        ]
        
        # Lấy ra cả chữ và emoji theo chu kỳ
        current_text, current_emoji = statuses[bot.status_index % len(statuses)]
        bot.status_index += 1
        
        # Xử lý ép kiểu: Nếu là string (mã thô), convert sang PartialEmoji
        final_emoji = None
        if current_emoji and isinstance(current_emoji, str):
            final_emoji = discord.PartialEmoji.from_str(current_emoji)
        else:
            final_emoji = current_emoji
        
        # Ép cố định chế độ mặt trăng (Idle) và truyền chuẩn vào 2 tham số name và emoji
        activity = discord.CustomActivity(name=current_text, emoji=final_emoji)
        await bot.change_presence(status=discord.Status.idle, activity=activity)
    except Exception as e:
        print(f"[STATUS ERROR] {e}", flush=True)

@rotate_status.before_loop
async def before_rotate_status():
    await bot.wait_until_ready()

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
    "commands.fun.yiyi_resources",
    "commands.emoji.emoji_sync",
    "commands.dev.dev_emojis",  # [CẤY MỚI PREMIUM] Mở rộng trình đăng ký quản lý biến emoji hệ thống tối cao
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

    # [CẤY MỚI] Khởi động vòng lặp an toàn không block event loop
    if not rotate_status.is_running():
        rotate_status.start()

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
        
        # [CẤY MỚI PREMIUM - ĐÚNG NIÊN ĐẠI HẠ TẦNG] Nạp toàn bộ biến động vào RAM trước khi các Cogs được load
        try:
            from commands.dev.dev_emojis import load_dynamic_emojis
            await load_dynamic_emojis(bot)
        except Exception as e:
            print(f"[PREMIUM BOOT ERROR] Mạch đồng bộ nạp RAM Emoji biến động thất bại: {e}", flush=True)
            
    else:
        print("[DB WARNING] Không tìm thấy MONGO_URI. Bot đang chạy chế độ RAM-Only!", flush=True)

    # [FIX CỐT LÕI] Gọi await trực tiếp, không dùng create_task để tránh phá vỡ Event Loop
    await start_web_server()
    
    await load_extensions()
    
    # bot.start() sẽ tự động giữ cho chương trình chạy vô tận, không cần Event().wait() nữa
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("[EXIT] Bot đã tắt an toàn.")
