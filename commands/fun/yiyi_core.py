import discord
from discord import app_commands
from discord.ext import commands
import time
import random
import asyncio
import traceback

# Nhập hệ Emojis của PeiD
from utils.emojis import Emojis

# Nạp Storage thực tế - Tuyệt đối không thay đổi logic gốc của Nguyệt
from core.greet_storage import get_guild_config as get_greet_cfg
from core.booster_storage import get_guild_config as get_booster_cfg
from core.ticket_storage import get_ticket_config
from core.embed_storage import get_all_embeds
from core.identity_storage import get_all_identities
from core.state import State

class YiyiGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="yiyi", description="hệ thống tương tác cá nhân hóa của yiyi")
        self.bot = bot

    # ==========================================
    # LỆNH 1: PING PRO (/yiyi oi) - GIỮ 100% CODE CỦA NGUYỆT
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
    # LỆNH 2: LOVE (/yiyi iu) - GIỮ 100% CODE CỦA NGUYỆT
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
    # LỆNH 3: SETTING (/yiyi setting) - BẢN TÁCH DÒNG CỰC DÀI & FIX UPDATE
    # ==========================================
    @app_commands.command(name="setting", description="kiểm tra chi tiết các cài đặt của server")
    async def setting(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            gid = interaction.guild.id
            gid_str = str(gid)

            # Nạp data đa luồng
            try:
                results = await asyncio.gather(
                    get_greet_cfg(gid), get_booster_cfg(gid), get_ticket_config(gid),
                    get_all_embeds(gid), get_all_identities(gid),
                    return_exceptions=True
                )
            except: results = [{}, {}, {}, {}, {}]

            greet_full = results[0] if isinstance(results[0], dict) else {}
            boost_cfg = results[1] if isinstance(results[1], dict) else {}
            ticket_cfg = results[2] if isinstance(results[2], dict) else {}
            embed_data = results[3] if isinstance(results[3], dict) else {}
            ident_data = results[4] if isinstance(results[4], dict) else {}

            # Reaction Role từ DB
            rr_count = 0
            db = getattr(State.bot, "db", None)
            if db is not None:
                rr_count = await db['reactions'].count_documents({"guild_id": gid_str})

            # Helper bóc tách đúng Key từ GreetStorage (Fix lỗi không update)
            def parse_greet(section_key):
                data = greet_full.get(section_key, {})
                c_id = data.get("channel_id")
                e_nm = data.get("embed_name")
                msg = data.get("message")
                status = f"`ON`" if (c_id or e_nm or msg) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", f"`{e_nm}`" if e_nm else f"`none`", f"`có`" if msg else f"`none`"

            # Helper bóc tách đúng Key từ BoosterStorage
            def parse_booster():
                c_id = boost_cfg.get("channel")
                e_nm = boost_cfg.get("embed")
                msg = boost_cfg.get("message")
                r_id = boost_cfg.get("booster_role")
                status = f"`ON`" if (c_id or e_nm or msg or r_id) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", f"`{e_nm}`" if e_nm else f"`none`", f"`có`" if msg else f"`none`", f"<@&{r_id}>" if r_id else f"`none`"

            # Đếm số lượng identity (vỏ)
            id_count = len(ident_data) if isinstance(ident_data, dict) else 0

            # Phân tách Greet/Leave/Wellcome/Booster
            g_st, g_ch, g_eb, g_tx = parse_greet("greet")
            l_st, l_ch, l_eb, l_tx = parse_greet("leave")
            w_st, w_ch, w_eb, w_tx = parse_greet("wellcome")
            b_st, b_ch, b_eb, b_tx, b_rl = parse_booster()

            # Đếm embed có nút
            embed_with_buttons = sum(1 for e in embed_data.values() if isinstance(e, dict) and e.get("buttons"))

            # Ticket Mapping
            t_st = f"`ON`" if ticket_cfg.get("category_id") else f"`OFF`"
            s_roles = ticket_cfg.get("staff_roles", [])
            t_rl = f"<@&{s_roles[0]}>" if (isinstance(s_roles, list) and s_roles) else f"<@&{s_roles}>" if s_roles else f"`none`"

            # ================= RÁP DASHBOARD SIÊU DÀI - DNA NGUYÊN BẢN =================
            desc = f"""{Emojis.MATTRANG} **hệ thống tiếp tân & tương tác**
• **greet (chào mừng)**: {g_st}
  └ kênh: {g_ch}
  └ embed: {g_eb}
  └ text: {g_tx}
• **leave (tạm biệt)**: {l_st}
  └ kênh: {l_ch}
  └ embed: {l_eb}
  └ text: {l_tx}
• **wellcome (chào mừng 2)**: {w_st}
  └ kênh: {w_ch}
  └ embed: {w_eb}
  └ text: {w_tx}
• **booster (tri ân)**: {b_st}
  └ kênh: {b_ch}
  └ embed: {b_eb}
  └ text: {b_tx}
  └ role: {b_rl}

{Emojis.MATTRANG} **kho lưu trữ embed**
• **số embed đã tạo**: `{len(embed_data)}/50`
• **số embed liên kết nút bấm**: `{embed_with_buttons}`
• **reaction role**: `{rr_count}` (tính theo id embed đã gửi đi)

{Emojis.MATTRANG} **tiện ích button**
• **ticket (hỗ trợ)**: {t_st}
  └ embed: `{ticket_cfg.get('embed_name', 'none')}`
  └ role hỗ trợ: {t_rl}
  └ danh mục: <#{ticket_cfg.get('category_id', 'none')}>
  └ kênh gửi log: <#{ticket_cfg.get('log_channel_id', 'none')}>
• **identity (giả danh)**:
  └ số vỏ: `{id_count}`"""

            report = discord.Embed(title=f"{Emojis.MATTRANG} **chi tiết cấu hình của** {interaction.guild.name}", description=desc, color=0xf8bbd0)
            report.set_footer(text="yiyi iu cậu • báo cáo chi tiết linh kiện cloud")
            await interaction.followup.send(embed=report)
        except: 
            traceback.print_exc()

async def setup(bot: commands.Bot):
    bot.tree.add_command(YiyiGroup(bot))
    print("[load] success: commands.fun.yiyi_core (Full DNA + Long Dashboard)")
