import discord
from discord import app_commands
from discord.ext import commands
import time
import random
import asyncio
import traceback

# Nhập hệ Emojis của PeiD
from utils.emojis import Emojis

# Nạp sẵn Storage để tối ưu tốc độ
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
            await interaction.response.defer(ephemeral=False)
            start_time = time.perf_counter()
            ws_latency = round(self.bot.latency * 1000)
            is_boss = interaction.user.id == getattr(self.bot, "boss_id", 1055476307372294155)

            if is_boss:
                responses = [
                    f"**yiyi** đây nè **Nguyệt**. có việc gì muốn nhờ **yiyi** he? {Emojis.HOICHAM}",
                    f"haii, **yiyi** ở đây chờ **Nguyệt** chỉ thị nè {Emojis.YIYITIM}",
                    f"**Nguyệt** gọi vì nhớ **yiyi** phải hong? {Emojis.YIYITIM}"
                ]
            else:
                responses = ["haiiii, **yiyi** đâyyy", "**yiyi** có mặt", f"gọi **yiyi** có chuyện gì hee? {Emojis.HOICHAM}"]
            
            end_time = time.perf_counter()
            api_latency = round((end_time - start_time) * 1000)
            
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
            # Tốc biến defer lên trước để ép Discord không được văng lỗi Timeout 10062
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            print(f"[CRITICAL] Không thể defer interaction: {e}", flush=True)
            return

        guild = interaction.guild
        guild_id = guild.id

        try:
            # Nạp dữ liệu đa luồng
            results = await asyncio.gather(
                get_guild_config(guild_id),
                get_ticket_config(guild_id),
                get_all_embeds(guild_id),
                return_exceptions=True
            )
            
            greet_data = results[0] if isinstance(results[0], dict) else {}
            ticket_cfg = results[1] if isinstance(results[1], dict) else {}
            all_embeds = results[2] if isinstance(results[2], (dict, list)) else []
            
            # --- HELPER: KHAI QUẬT CHI TIẾT TỪNG LINH KIỆN ---
            def get_detail(module_data):
                if not module_data or not isinstance(module_data, dict):
                    return "`chưa thiết lập`"
                
                comps = []
                if module_data.get("channel_id"): comps.append("kênh (channel)")
                if module_data.get("embed_name"): comps.append("giao diện (embed)")
                if module_data.get("message"): comps.append("tin nhắn (text)")
                if module_data.get("ping_role"): comps.append("thẻ (role)")
                    
                return f"{Emojis.YIYITIM} (đã kích hoạt: " + ", ".join(comps) + ")" if comps else "`chưa thiết lập`"

            # --- HELPER: ĐẾM NÚT BẤM VÀ EMBED (CHỐNG LỖI CẤU TRÚC DB) ---
            total_btns = 0
            linked_embeds = 0
            
            embed_list = all_embeds.values() if isinstance(all_embeds, dict) else all_embeds
            for emb in embed_list:
                if isinstance(emb, dict):
                    btns = emb.get("buttons", [])
                    if btns:
                        total_btns += len(btns)
                        linked_embeds += 1

            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} Chi tiết cấu hình của {guild.name}",
                description="Hệ thống đã quét toàn bộ các thiết lập và tinh chỉnh hiện tại của server.",
                color=0xf8bbd0
            )

            # Nhánh Greet/Leave/Wellcome/Booster
            greet_sec = greet_data.get('greet', {}) if isinstance(greet_data, dict) else {}
            greet_sec = greet_sec if isinstance(greet_sec, dict) else {}
            booster_data = greet_sec.get('booster_channel')
            booster_status = f"{Emojis.YIYITIM} (đã kích hoạt kênh thông báo)" if booster_data else "`chưa thiết lập`"
            
            embed.add_field(
                name=f"{Emojis.YIYITIM} HỆ THỐNG LỜI CHÀO & TƯƠNG TÁC",
                value=(
                    f"• **greet (chào mừng):** {get_detail(greet_data.get('greet') if isinstance(greet_data, dict) else None)}\n"
                    f"• **leave (tạm biệt):** {get_detail(greet_data.get('leave') if isinstance(greet_data, dict) else None)}\n"
                    f"• **wellcome (xác thực):** {get_detail(greet_data.get('wellcome') if isinstance(greet_data, dict) else None)}\n"
                    f"• **booster (tri ân):** {booster_status}"
                ),
                inline=False
            )

            # Nhánh Embed & Interaction
            total_embeds_count = len(all_embeds) if isinstance(all_embeds, (dict, list)) else 0
            embed.add_field(
                name=f"{Emojis.MATTRANG} KHO LƯU TRỮ EMBED",
                value=(
                    f"• **tổng số embed:** `{total_embeds_count}/50` bản ghi đã tạo\n"
                    f"• **tương tác nút bấm:** `{total_btns}` nút được gắn trên `{linked_embeds}` embed\n"
                    f"• **reaction role:** hệ thống đang theo dõi qua message id"
                ),
                inline=False
            )

            # Nhánh Tính năng nâng cao (Ticket, Form)
            ticket_status = "`chưa thiết lập`"
            if isinstance(ticket_cfg, dict):
                t_comp = []
                if ticket_cfg.get("category_id"): t_comp.append("danh mục (category)")
                if ticket_cfg.get("staff_roles"): t_comp.append("nhân viên (staff)")
                if ticket_cfg.get("log_channel_id"): t_comp.append("nhật ký (logs)")
                if t_comp: ticket_status = f"{Emojis.YIYITIM} (đã kích hoạt: " + ", ".join(t_comp) + ")"

            embed.add_field(
                name=f"{Emojis.HOICHAM} TIỆN ÍCH QUẢN TRỊ CAO CẤP",
                value=(
                    f"• **ticket (hỗ trợ):** {ticket_status}\n"
                    f"• **form (biểu mẫu):** `tự động đồng bộ theo tên embed`\n"
                    f"• **identity (hồ sơ):** `active` (đang hoạt động)\n"
                    f"• **link (mạng lưới):** `active` (đang hoạt động)"
                ),
                inline=False
            )

            embed.set_footer(text="yiyi iu cậu • báo cáo chi tiết linh kiện cloud")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"\n[CRITICAL ERROR] --- BẮT ĐẦU DÒ LỖI YIYI SETTING ---", flush=True)
            traceback.print_exc()
            print(f"--- KẾT THÚC DÒ LỖI ---\n", flush=True)
            
            try:
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
