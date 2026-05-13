import discord
from discord import app_commands
from discord.ext import commands
import time
import random
import asyncio
import traceback

# Nhập hệ Emojis của PeiD
from utils.emojis import Emojis

# Nạp Storage thực tế
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
    # LỆNH 1: PING PRO (/yiyi oi) - GIỮ 100% GỐC
    # ==========================================
    @app_commands.command(name="oi", description="gọi yiyi để kiểm tra tốc độ hệ thống")
    async def oi(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=False)
            start_time = time.perf_counter()
            ws_latency = round(self.bot.latency * 1000)
            is_boss = interaction.user.id == 1055476307372294155

            if is_boss:
                responses = [
                    f"**yiyi** đây nè **Nguyệt**. có việc gì muốn nhờ **yiyi** he? {Emojis.HOICHAM}",
                    f"haii, **yiyi** ở đây chờ **Nguyệt** chỉ thị nè {Emojis.YIYITIM}",
                    f"**Nguyệt** gọi vì nhớ **yiyi** phải hong? {Emojis.YIYITIM}"
                ]
            else:
                responses = ["haiiii, **yiyi** đâyyy", "**yiyi** có mặt", f"gọi **yiyi** có chuyện gì hee? {Emojis.HOICHAM}"]
            
            api_latency = round((time.perf_counter() - start_time) * 1000)
            embed = discord.Embed(
                title=random.choice(responses),
                description=f"tốc độ xử lý (api): **{api_latency}ms** • tín hiệu (ws): **{ws_latency}ms**",
                color=0xf8bbd0
            )
            embed.set_footer(text=f"hệ thống ổn định • shard: 0")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"[yiyi_oi error] {e}", flush=True)

    # ==========================================
    # LỆNH 2: LOVE (/yiyi iu) - GIỮ 100% GỐC
    # ==========================================
    @app_commands.command(name="iu", description="hỏi xem yiyi thương ai nhất")
    async def iu(self, interaction: discord.Interaction):
        try:
            is_boss = interaction.user.id == 1055476307372294155
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
            
            await interaction.response.send_message(
                embed=discord.Embed(title=random.choice(responses), color=0xf8bbd0)
            )
        except Exception as e:
            print(f"[yiyi_iu error] {e}", flush=True)

    # ==========================================
    # LỆNH 3: SETTING (/yiyi setting) - BẢN DÀI TÁCH DÒNG & FIX UPDATE
    # ==========================================
    @app_commands.command(name="setting", description="kiểm tra chi tiết các cài đặt của server")
    async def setting(self, interaction: discord.Interaction):
        try:
            # Defer ngay lập tức để tránh Unknown Interaction khi nạp database chậm
            await interaction.response.defer(ephemeral=True)
            gid = interaction.guild.id
            gid_str = str(gid)

            # NẠP DATA ĐA LUỒNG
            try:
                try: 
                    from core.forms_storage import get_forms_config
                    form_task = get_forms_config(gid)
                except: 
                    async def dummy_f(g): return {}
                    form_task = dummy_f(gid)
                
                results = await asyncio.gather(
                    get_greet_cfg(gid), get_booster_cfg(gid), get_ticket_config(gid),
                    get_all_embeds(gid), form_task, get_all_identities(gid),
                    return_exceptions=True
                )
            except: 
                results = [{}, {}, {}, {}, {}, {}]

            # Lấy đúng nhánh settings để fix lỗi không update
            greet_root = results[0] if isinstance(results[0], dict) else {}
            greet_settings = greet_root.get("settings", {})
            
            boost_cfg = results[1] if isinstance(results[1], dict) else {}
            ticket_cfg = results[2] if isinstance(results[2], dict) else {}
            embed_data = results[3] if isinstance(results[3], dict) else {}
            form_cfg = results[4] if isinstance(results[4], dict) else {}
            ident_data = results[5] if isinstance(results[5], dict) else {}

            rr_count = 0
            try:
                db = getattr(State.bot, "db", None)
                if db is not None:
                    rr_count = await db['reactions'].count_documents({"guild_id": gid_str})
            except: pass

            # --- HELPER ĐỊNH DẠNG TÁCH DÒNG ---
            def parse_module(module_key):
                data = greet_settings.get(module_key, {})
                c_id, e_nm, msg = data.get("channel_id"), data.get("embed_name"), data.get("message")
                status = f"`ON`" if (c_id or e_nm or msg) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", f"`{e_nm}`" if e_nm else f"`none`", f"`có`" if msg else f"`none`"

            def parse_booster():
                c_id = boost_cfg.get("channel")
                e_nm = boost_cfg.get("embed")
                msg = boost_cfg.get("message")
                r_id = boost_cfg.get("booster_role")
                status = f"`ON`" if (c_id or e_nm or msg or r_id) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", f"`{e_nm}`" if e_nm else f"`none`", f"`có`" if msg else f"`none`", f"<@&{r_id}>" if r_id else f"`none`"

            g_st, g_ch, g_eb, g_tx = parse_module("greet")
            l_st, l_ch, l_eb, l_tx = parse_module("leave")
            w_st, w_ch, w_eb, w_tx = parse_module("wellcome")
            b_st, b_ch, b_eb, b_tx, b_rl = parse_booster()

            embed_with_buttons = sum(1 for e in embed_data.values() if isinstance(e, dict) and e.get("buttons"))
            t_rl = f"<@&{ticket_cfg.get('staff_roles')[0]}>" if (ticket_cfg.get('staff_roles') and isinstance(ticket_cfg.get('staff_roles'), list)) else f"<@&{ticket_cfg.get('staff_roles')}>" if ticket_cfg.get('staff_roles') else "`none`"

            # ================= RÁP DASHBOARD SIÊU DÀI THEO Ý NGUYỆT =================
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
• **reaction role**: `{rr_count}`

{Emojis.MATTRANG} **tiện ích button**
• **ticket (hỗ trợ)**: {t_st}
  └ embed: `{ticket_cfg.get('embed_name', 'none')}`
  └ role hỗ trợ: {t_rl}
  └ danh mục: <#{ticket_cfg.get('category_id', 'none')}>
  └ kênh gửi log: <#{ticket_cfg.get('log_channel_id', 'none')}>
• **form (tuỳ chọn)**: {f_st}
  └ embed: `{form_cfg.get('embed_name', 'none')}`
  └ số ô nhập liệu: `{len(form_cfg.get('fields', []))}`
  └ tiêu đề: `{form_cfg.get('title', 'none')}`
  └ thumbnail: {f_th}
  └ kênh gửi log: <#{form_cfg.get('log_channel_id', 'none')}>
• **identity (giả danh)**:
  └ số vỏ: `{len(ident_data)}`"""

            report = discord.Embed(title=f"{Emojis.MATTRANG} **chi tiết cấu hình của** {interaction.guild.name}", description=desc, color=0xf8bbd0)
            report.set_footer(text="yiyi iu cậu • báo cáo chi tiết linh kiện cloud")
            await interaction.followup.send(embed=report)
        except Exception as e:
            traceback.print_exc()

async def setup(bot: commands.Bot):
    bot.tree.add_command(YiyiGroup(bot))
