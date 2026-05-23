import discord
from discord.ext import commands, tasks
import asyncio
import os
from aiohttp import web

from core.state import State
from core.mongodb import MongoDB 
from utils.emojis import Emojis

# ==========================================
# [GIẢI PHÁP TỐI THƯỢNG] TỰ CẠY FILE .ENV
# ==========================================
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')

_TOKEN = None
_MONGO_URI = None

if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith("TOKEN="):
                _TOKEN = line.split("=", 1)[1].strip(' "\'')
            elif line.startswith("MONGO_URI="):
                _MONGO_URI = line.split("=", 1)[1].strip(' "\'')

if _TOKEN: os.environ["TOKEN"] = _TOKEN
if _MONGO_URI: os.environ["MONGO_URI"] = _MONGO_URI

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("Vẫn không có TOKEN!")

# =========================
# WEB SERVER
# =========================
async def health(request):
    return web.Response(text="PeiD Bot is online and healthy!")

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
    help_command=None,
    status=discord.Status.idle,
    activity=discord.CustomActivity(name="˚₊‧꒰ა yiyi iu ໒꒱ ‧₊˚")
)

bot.boss_id = 1055476307372294155
State.bot = bot 

# =========================
# [CẤY MỚI] HỆ THỐNG VÒNG LẶP STATUS CHIẾN LƯỢC
# =========================
bot.status_index = 0

@tasks.loop(seconds=30)
async def rotate_status():
    try:
        # Sử dụng Tên biến dưới dạng String để truy vấn động thông qua getattr
        # Điều này giúp bot không bị crash nếu biến chưa kịp được nạp từ DB
        statuses = [
            ("˚₊‧꒰ა yiyi iu ໒꒱ ‧₊˚", None),
            ("vương dỹ nguyệt", "NO"),
            ("vạn diệp  〆  ≋", "HT")
        ]
        
        current_text, emoji_key = statuses[bot.status_index % len(statuses)]
        bot.status_index += 1
        
        # Lấy giá trị biến từ class Emojis một cách an toàn
        emoji_val = getattr(Emojis, emoji_key, None) if emoji_key else None
        
        # Xử lý ép kiểu: Nếu là string (mã thô), convert sang PartialEmoji
        final_emoji = None
        if emoji_val and isinstance(emoji_val, str):
            final_emoji = discord.PartialEmoji.from_str(emoji_val)
        else:
            final_emoji = emoji_val
        
        activity = discord.CustomActivity(name=current_text, emoji=final_emoji)
        await bot.change_presence(status=discord.Status.idle, activity=activity)
    except Exception as e:
        print(f"[STATUS ERROR] {e}", flush=True)

@rotate_status.before_loop
async def before_rotate_status():
    await bot.wait_until_ready()

# =========================
# EXTENSIONS
# =========================
EXTENSIONS = [
    "core.root", "systems.button_listener", "commands.embed.embed_group", 
    "core.greet_leave", "core.wellcome", "core.booster", "systems.reaction_role", 
    "commands.fun.yiyi_core", "commands.embed.embed_advanced", "commands.embed.embed_webhook", 
    "commands.embed.embed_link", "commands.identity.identity_group", "commands.ticket.ticket_group", 
    "commands.forms.forms_group", "commands.fun.yiyi_resources", "commands.emoji.emoji_sync", "commands.dev.dev_emojis"
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
# READY STATE
# =========================
bot._ready_once = False

@bot.event
async def on_ready():
    if bot._ready_once: return
    bot._ready_once = True

    if not rotate_status.is_running():
        rotate_status.start()

    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] ✅ Thành công! Đã đồng bộ {len(synced)} lệnh Slash.", flush=True)
    except Exception as e:
        print(f"[SLASH ERROR] {e}", flush=True)

    print(f"🚀 {bot.user} đã sẵn sàng phục vụ!", flush=True)

# =========================
# MAIN ENTRY
# =========================
async def main():
    discord.utils.setup_logging()
    uri = os.getenv("MONGO_URI")
    if uri:
        bot.db = MongoDB(uri)
        await bot.db.connect()
        try:
            from commands.dev.dev_emojis import load_dynamic_emojis
            await load_dynamic_emojis(bot)
        except Exception as e:
            print(f"[PREMIUM BOOT ERROR] {e}", flush=True)
            
    await start_web_server()
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
