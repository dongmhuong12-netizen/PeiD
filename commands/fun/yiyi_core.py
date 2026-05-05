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

            # KIỂM TRA ĐẶC QUYỀN BOSS (NGUYỆT)
            is_boss = interaction.user.id == getattr(self.bot, "boss_id", 1055476307372294155)

            if is_boss:
                responses = [
                    f"**yiyi** đây nè **Nguyệt**. có việc gì muốn nhờ **yiyi** he? {Emojis.HOICHAM}",
                    f"haii, **yiyi** ở đây chờ **Nguyệt** chỉ thị nè {Emojis.YIYITIM}",
                    f"**Nguyệt** gọi vì nhớ **yiyi** phải hong? {Emojis.YIYITIM}"
                ]
            else:
                responses = [
                    "haiii, **yiyi** đâyyy",
                    "**yiyi** có mặt",
                    f"gọi **yiyi** có chuyện gì hee? {Emojis.HOICHAM}"
                ]
            
            embed = discord.Embed(
                title=random.choice(responses),
                description=f"tốc độ xử lý (api): **{api_latency}ms** • tín hiệu (ws): **{ws_latency}ms**",
                color=0xf8bbd0
            )
            
            shard_id = interaction.guild.shard_id if interaction.guild and self.bot.shard_count else 0
            embed.set_footer(text=f"hệ thống ổn định • shard: {shard_id}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"[yiyi_oi error] fail to fetch ping: {e}", flush=True)
            if not interaction.response.is_done():
                await interaction.followup.send("**yiyi** đang bị nghẽn mạng chút xíu nha!", ephemeral=True)

    # ==========================================
    # LỆNH 2: LOVE (/yiyi iu)
    # ==========================================
    @app_commands.command(name="iu", description="hỏi xem yiyi thương ai nhất")
    async def iu(self, interaction: discord.Interaction):
        try:
            # KIỂM TRA ĐẶC QUYỀN BOSS (NGUYỆT)
            is_boss = interaction.user.id == getattr(self.bot, "boss_id", 1055476307372294155)

            if is_boss:
                responses = [
                    f"**yiyi** yêu người nhấttt {Emojis.YIYITIM}",
                    f"**yiyi** cũng iu cậu nhất {Emojis.YIYITIM}",
                    f"iu **Vương Dỹ Nguyệt** nhất luôn {Emojis.YIYITIM}"
                ]
            else:
                responses = [
                    f"**yiyi** cũng iu **yiyi** lắm {Emojis.YIYITIM}",
                    "ehe ₍₍ (̨̡⸝⸝´꒳`⸝⸝)̧̢ ₎₎",
                    f"ủa gì zạ {Emojis.HOICHAM}"
                ]

            embed = discord.Embed(
                title=random.choice(responses),
                color=0xf8bbd0
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"[yiyi_iu error] {e}", flush=True)

# ==========================================
# INJECTION (ĐĂNG KÝ VÀO CÂY LỆNH TỔNG)
# ==========================================
async def setup(bot: commands.Bot):
    try:
        bot.tree.add_command(YiyiGroup(bot))
        print("[load] success: commands.fun.yiyi_core (sweet personality loaded)", flush=True)
    except Exception as e:
        print(f"[load error] failed to inject yiyi_core: {e}", flush=True)
