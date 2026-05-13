import discord
from discord import app_commands
from discord.ext import commands
import time
import random
import asyncio
import traceback # [CẤY MỚI] Công cụ dò lỗi tàng hình chuẩn IT Pro

# Nhập hệ Emojis của PeiD
from utils.emojis import Emojis

# Nạp sẵn Storage để tối ưu tốc độ phản hồi 
from core.greet_storage import get_guild_config
from core.ticket_storage import get_ticket_config
from core.embed_storage import get_all_embeds

class YiyiGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="yiyi", description="hệ thống tương tác cá nhân hóa của yiyi")
        self.bot = bot

    # ==========================================
    # LỆNH 1: PING PRO (/yiyi oi)
    # ==========================================
    @app_commands.command(name="oi", description="gọi yiyi để kiểm tra tốc độ hệ thống")
    async def oi(self, interaction: discord.Interaction):
        try:
            start_time = time.perf_counter()
            await interaction.response.defer(ephemeral=False)
            end_time = time.perf_counter()
            
            api_latency = round((end_time - start_time) * 1000)
            ws_latency = round(self.bot.latency * 1000)
            is_boss = interaction.user.id == getattr(self.bot, "boss_id", 1055476307372294155)

            if is_boss:
                responses = [
                    f"**yiyi** đây nè **Nguyệt**. có việc gì muốn nhờ **yiyi** he? {Emojis.HOICHAM}",
                    f"haii, **yiyi** ở đây chờ **Nguyệt** chỉ thị nè {Emojis.YIYITIM}",
                    f"**Nguyệt** gọi vì nhớ **yiyi** phải hong? {Emojis.YIYITIM}"
                ]
            else:
                responses = [
                    "haiiii, **yiyi** đâyyy",
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

    # ==========================================
    # LỆNH 2: LOVE (/yiyi iu)
    # ==========================================
    @app_commands.command(name="iu", description="hỏi xem yiyi thương ai nhất")
    async def iu(self, interaction: discord.Interaction):
        try:
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

            embed = discord.Embed(title=random.choice(responses), color=0xf8bbd0)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"[yiyi_iu error] {e}", flush=True)

    # ==========================================
    # LỆNH 3: SETTING (/yiyi setting)
    # ==========================================
    @app_commands.command(name="setting", description="kiểm tra chi tiết các cài đặt của server")
    async def setting(self, interaction: discord.Interaction):
        try:
            # Đưa defer vào trong try để nếu văng lỗi 40060 nó cũng bị Traceback tóm cổ
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            guild_id = guild.id

            # --- Tích hợp Parallel Loading ---
            greet_task = get_guild_config(guild_id)
            ticket_task = get_ticket_config(guild_id)
            embed_task = get_all_embeds(guild_id) 
            
            results = await asyncio.gather(greet_task, ticket_task, embed_task, return_exceptions=True)
            
            greet_data = results[0] if not isinstance(results[0], Exception) and results[0] else {}
            ticket_cfg = results[1] if not isinstance(results[1], Exception) and results[1] else {}
            all_embeds = results[2] if not isinstance(results[2], Exception) and results[2] else []
            
            # --- HELPER: SOI CHI TIẾT LINH KIỆN ---
            def get_detail(module_data):
                if not module_data:
                    return "`chưa thiết lập`"
                
                comps = []
                if module_data.get("channel_id"):
                    comps.append("channel")
                if module_data.get("embed_name"):
                    comps.append("embed")
                if module_data.get("message"):
                    comps.append("message")
                    
                if not comps:
                    return "`chưa thiết lập`"
                
                return f"{Emojis.YIYITIM} (đã setup: " + ", ".join(comps) + ")"

            # --- HELPER: ĐẾM NÚT BẤM (BUTTON) ---
            total_btns = 0
            linked_embeds = 0
            for emb in all_embeds:
                btns = emb.get("buttons", [])
                if btns:
                    total_btns += len(btns)
                    linked_embeds += 1

            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} Chi tiết các cài đặt của {guild.name}",
                color=0xf8bbd0
            )

            # Nhánh Greet/Leave/Wellcome/Booster
            booster_status = "`đã có channel`" if greet_data.get('greet', {}).get('booster_channel') else "`chưa thiết lập`"
            embed.add_field(
                name=f"{Emojis.YIYITIM} HỆ THỐNG LỜI CHÀO",
                value=(
                    f"• **greet:** {get_detail(greet_data.get('greet'))}\n"
                    f"• **leave:** {get_detail(greet_data.get('leave'))}\n"
                    f"• **wellcome:** {get_detail(greet_data.get('wellcome'))}\n"
                    f"• **booster:** {booster_status}"
                ),
                inline=False
            )

            # Nhánh Embed & Interaction
            embed.add_field(
                name=f"{Emojis.MATTRANG} TƯƠNG TÁC & EMBED",
                value=(
                    f"• **embed:** `{len(all_embeds)}/50` (số lượng đã tạo)\n"
                    f"• **button:** `{total_btns}` nút bấm trên `{linked_embeds}` embed\n"
                    f"• **reaction role:** (kiểm tra theo message id)"
                ),
                inline=False
            )

            # Nhánh Tính năng nâng cao (Soi Ticket)
            ticket_status = "`chưa thiết lập`"
            if ticket_cfg:
                t_comp = []
                if ticket_cfg.get("category_id"): t_comp.append("category")
                if ticket_cfg.get("staff_roles"): t_comp.append("staff")
                if ticket_cfg.get("log_channel_id"): t_comp.append("logs")
                if t_comp: ticket_status = f"{Emojis.YIYITIM} (đã setup: " + ", ".join(t_comp) + ")"

            embed.add_field(
                name=f"{Emojis.HOICHAM} TIỆN ÍCH HỆ THỐNG",
                value=(
                    f"• **ticket:** {ticket_status}\n"
                    f"• **form:** (kiểm tra theo từng tên embed)\n"
                    f"• **identity:** `active`\n"
                    f"• **link:** `active`"
                ),
                inline=False
            )

            embed.set_footer(text="yiyi iu cậu • báo cáo chi tiết linh kiện cloud")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            # [IT PRO] Dùng Traceback để in đích danh dòng lỗi ra log Render
            print(f"\n[CRITICAL ERROR] --- BẮT ĐẦU DÒ LỖI YIYI SETTING ---", flush=True)
            traceback.print_exc()
            print(f"--- KẾT THÚC DÒ LỖI ---\n", flush=True)
            
            try:
                # Gửi nguyên cái tên lỗi ra kênh Discord để Nguyệt thấy ngay lập tức
                error_name = repr(e)
                await interaction.followup.send(f"{Emojis.HOICHAM} yiyi gặp lỗi khi quét dữ liệu! Mã lỗi: `{error_name}` (Soi log Render ngay sếp ơi)", ephemeral=True)
            except Exception:
                pass

# ==========================================
# INJECTION (ĐĂNG KÝ VÀO CÂY LỆNH TỔNG)
# ==========================================
async def setup(bot: commands.Bot):
    try:
        bot.tree.add_command(YiyiGroup(bot))
        print("[load] success: commands.fun.yiyi_core (sweet personality loaded)", flush=True)
    except Exception as e:
        print(f"[load error] failed to inject yiyi_core: {e}", flush=True)
