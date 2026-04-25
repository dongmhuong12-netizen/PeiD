import discord
from discord.ext import commands
from discord import app_commands

# Chỉ giữ lại các Listener hệ thống
from core.greet_leave import GreetLeaveListener
from core.booster import BoosterListener
from core.wellcome import WellcomeListener

# =============================
# MAIN GROUP (CHỈ TẠO KHUNG /P)
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="Hệ thống lệnh PeiD Core")

# =============================
# ROOT COG (XỬ LÝ CHUNG)
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    # Bước 1: Tạo lệnh gốc /p nếu chưa tồn tại trong cây lệnh
    if bot.tree.get_command("p") is None:
        bot.tree.add_command(PGroup())
        print("[ROOT] Khung lệnh /p đã được dựng.", flush=True)

    # Bước 2: Nạp các thành phần Cog và Listener
    await bot.add_cog(Root(bot))
    await bot.add_cog(GreetLeaveListener(bot))
    await bot.add_cog(BoosterListener(bot))
    await bot.add_cog(WellcomeListener(bot))
    print("[ROOT] Toàn bộ Listener hệ thống đã sẵn sàng.", flush=True)
