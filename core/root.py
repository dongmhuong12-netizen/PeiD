import discord
from discord.ext import commands
from discord import app_commands

# =============================
# MAIN GROUP (CHỈ TẠO KHUNG /P)
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="hệ thống lệnh peiD core")

# =============================
# ROOT COG (QUẢN LÝ CHUNG)
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    """
    nhiệm vụ: khởi tạo nền móng cho toàn bộ hệ thống lệnh /p.
    không nạp hộ listener của module khác để tránh lỗi load chồng (already loaded).
    """
    
    # 1. kiểm tra và dựng khung lệnh gốc /p
    if bot.tree.get_command("p") is None:
        bot.tree.add_command(PGroup())
        print("[root] khung lệnh /p đã được dựng.", flush=True)

    # 2. nạp cog quản lý chung
    await bot.add_cog(Root(bot))
    print("[root] hệ thống root đã sẵn sàng.", flush=True)
