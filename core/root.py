import discord
from discord.ext import commands
from discord import app_commands

# =============================
# MAIN GROUP (CHỈ TẠO KHUNG /P)
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="hệ thống lệnh peiD core")

# [THÊM MỚI] BỘ KHUNG PHASE 3: OMNI-INTERACTION (CONTAINER TẬP TRUNG)
class ButtonGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="button", description="hệ thống quản lý nút bấm tương tác (phase 3)")

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

    # [THÊM MỚI] 1.5. Thiết lập "Đại bản doanh" cho nhánh /p button (Chuẩn Multi-IT)
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Cơ chế Safe Injection: Tháo nhánh cũ nếu reload để chống lỗi trùng lặp
        existing_button = next((cmd for cmd in p_cmd.commands if cmd.name == "button"), None)
        if existing_button:
            p_cmd.remove_command("button")
        
        # Tiêm vỏ chứa ButtonGroup vào lõi /p
        p_cmd.add_command(ButtonGroup())
        print("[root] nhánh /p button (omni-interaction) đã được tiêm an toàn.", flush=True)

    # 2. nạp cog quản lý chung
    await bot.add_cog(Root(bot))
    print("[root] hệ thống root đã sẵn sàng.", flush=True)


