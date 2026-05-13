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
    # LỆNH 3: SETTING (/yiyi setting)
    # ==========================================
    @app_commands.command(name="setting", description="kiểm tra chi tiết các cài đặt của server")
    async def setting(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        guild_id = guild.id

        # --- Nạp Trí Nhớ Cloud ---
        from core.greet_storage import get_guild_config
        from core.ticket_storage import get_ticket_config
        from core.embed_storage import get_all_embeds
        
        # 1. Thu thập dữ liệu
        greet_data = await get_guild_config(guild_id)
        ticket_cfg = await get_ticket_config(guild_id)
        all_embeds = await get_all_embeds(guild_id)
        
        def check_setup(module_data):
            if not module_data or not any(module_data.values() if isinstance(module_data, dict) else [module_data]):
                return "`chưa thiết lập`"
            return f"{Emojis.YIYITIM} `đã sẵn sàng`"

        # 2. Xây dựng nội dung hiển thị
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} Chi tiết các cài đặt của {guild.name}",
            color=0xf8bbd0
        )

        # Nhánh Greet/Leave/Wellcome/Booster
        booster_status = check_setup(greet_data.get('greet', {}).get('booster_channel'))
        embed.add_field(
            name=f"{Emojis.YIYITIM} HỆ THỐNG LỜI CHÀO",
            value=(
                f"• **greet:** {check_setup(greet_data.get('greet'))}\n"
                f"• **leave:** {check_setup(greet_data.get('leave'))}\n"
                f"• **wellcome:** {check_setup(greet_data.get('wellcome'))}\n"
                f"• **booster:** {booster_status}"
            ),
            inline=False
        )

        # Nhánh Embed & Interaction
        embed_count = len(all_embeds)
        # Giữ đúng hạn mức 100k+ server của Nguyệt
        embed.add_field(
            name=f"{Emojis.MATTRANG} TƯƠNG TÁC & EMBED",
            value=(
                f"• **embed:** `{embed_count}/50` (số lượng đã tạo)\n"
                f"• **reaction role:** (kiểm tra theo message id)\n"
                f"• **button:** `tự động đồng bộ`"
            ),
            inline=False
        )

        # Nhánh Tính năng nâng cao
        embed.add_field(
            name=f"{Emojis.HOICHAM} TIỆN ÍCH HỆ THỐNG",
            value=(
                f"• **ticket:** {check_setup(ticket_cfg)}\n"
                f"• **form:** (kiểm tra theo tên embed)\n"
                f"• **identity:** `active`\n"
                f"• **link:** `active`"
            ),
            inline=False
        )

        embed.set_footer(text="yiyi iu cậu • dữ liệu đã được Cloud hóa")
        await interaction.followup.send(embed=embed)

# ==========================================
# INJECTION (ĐĂNG KÝ VÀO CÂY LỆNH TỔNG)
# ==========================================
async def setup(bot: commands.Bot):
    try:
        bot.tree.add_command(YiyiGroup(bot))
        print("[load] success: commands.fun.yiyi_core (sweet personality loaded)", flush=True)
    except Exception as e:
        print(f"[load error] failed to inject yiyi_core: {e}", flush=True)
