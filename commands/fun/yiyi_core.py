import discord
from discord import app_commands
from discord.ext import commands
import time
import random

# Nhập hệ Emojis của PeiD
from utils.emojis import Emojis

class YiyiGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        # Đặt tên lệnh cha là /yiyi
        super().__init__(name="yiyi", description="hệ thống tương tác cá nhân hóa của yiyi")
        self.bot = bot

    # ==========================================
    # LỆNH 1: PING PRO (/yiyi oi)
    # ==========================================
    @app_commands.command(name="oi", description="gọi yiyi để kiểm tra tốc độ hệ thống")
    async def oi(self, interaction: discord.Interaction):
        try:
            # [IT PRO] Đo API Latency siêu chuẩn xác qua Defer
            start_time = time.perf_counter()
            await interaction.response.defer(ephemeral=False)
            end_time = time.perf_counter()
            
            api_latency = round((end_time - start_time) * 1000)
            ws_latency = round(self.bot.latency * 1000)

            # Ngân hàng câu thoại random
            responses = [
                f"**yiyi** đây, gọi **yiyi** vì nhớ phải hong? {Emojis.YIYITIM}",
                f"**yiyi** đây, có chuyện gì muốn nhờ **yiyi** giúp hee? {Emojis.HOICHAM}",
                f"haii, **yiyi** tới rùi nè {Emojis.MATTRANG}"
            ]
            
            embed = discord.Embed(
                title=random.choice(responses),
                description=f"tốc độ xử lý (api): **{api_latency}ms** • tín hiệu (ws): **{ws_latency}ms**",
                color=0xf8bbd0
            )
            
            # [TELEMETRY] Hỗ trợ Debug trên môi trường Multi-Shard (100k+ servers)
            shard_id = interaction.guild.shard_id if interaction.guild and self.bot.shard_count else 0
            embed.set_footer(text=f"hệ thống ổn định • shard: {shard_id}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            # [BẢO VỆ CỐT LÕI] Bắt lỗi ngầm, tránh sập cụm lệnh
            print(f"[yiyi_oi error] fail to fetch ping: {e}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("**yiyi** đang bị nghẽn mạng chút xíu, cậu thử lại sau nha!", ephemeral=True)

    # ==========================================
    # LỆNH 2: IDENTITY (/yiyi iu_ai)
    # ==========================================
    @app_commands.command(name="iu_ai", description="hỏi xem yiyi thương ai nhất")
    async def iu_ai(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title=f"**yiyi** iu **Vương Dỹ Nguyệt** nhấttt {Emojis.YIYITIM}",
                color=0xf8bbd0
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"[yiyi_iu_ai error] {e}", flush=True)

# ==========================================
# INJECTION (ĐĂNG KÝ VÀO CÂY LỆNH TỔNG)
# ==========================================
async def setup(bot: commands.Bot):
    try:
        # Nạp nguyên nhóm lệnh /yiyi vào Command Tree
        bot.tree.add_command(YiyiGroup(bot))
        print("[load] success: commands.fun.yiyi_core (identity engine loaded)", flush=True)
    except Exception as e:
        print(f"[load error] failed to inject yiyi_core: {e}", flush=True)


