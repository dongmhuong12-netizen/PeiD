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
    # LỆNH 1: PING PRO (/yiyi oi)
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
                color=0xe6e2dd
            )
            embed.set_footer(text=f"hệ thống ổn định • shard: 0")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"[yiyi_oi error] {e}", flush=True)

    # ==========================================
    # LỆNH 2: LOVE (/yiyi iu)
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
                embed=discord.Embed(title=random.choice(responses), color=0xe6e2dd)
            )
        except Exception as e:
            print(f"[yiyi_iu error] {e}", flush=True)

    # ==========================================
    # LỆNH 3: SETTING (/yiyi setting)
    # ==========================================
    @app_commands.command(name="setting", description="kiểm tra chi tiết các cài đặt của server")
    async def setting(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            gid = interaction.guild.id
            gid_str = str(gid)

            # NẠP DATA ĐA LUỒNG - TƯ DUY IT PRO
            try:
                results = await asyncio.gather(
                    get_greet_cfg(gid), get_booster_cfg(gid), get_ticket_config(gid),
                    get_all_embeds(gid), get_all_identities(gid),
                    return_exceptions=True
                )
            except: 
                results = [{}, {}, {}, {}, {}]

            greet_full = results[0] if isinstance(results[0], dict) else {}
            boost_cfg = results[1] if isinstance(results[1], dict) else {}
            ticket_cfg = results[2] if isinstance(results[2], dict) else {}
            embed_data = results[3] if isinstance(results[3], dict) else {}
            ident_data = results[4] if isinstance(results[4], dict) else {}

            # --- [BỘ LỌC CÁC LOẠI BUTTON] ---
            linked_form_names = set()
            links_by_embed = {} 

            for emb_name, emb_info in embed_data.items():
                if isinstance(emb_info, dict) and emb_info.get("buttons"):
                    for btn in emb_info["buttons"]:
                        cid = btn.get("custom_id", "")
                        if cid.startswith("yiyi:forms:open:"):
                            f_name = cid.split(":")[-1]
                            linked_form_names.add(f_name)
                        if btn.get("url"):
                            if emb_name not in links_by_embed:
                                links_by_embed[emb_name] = []
                            links_by_embed[emb_name].append(btn)

            rr_count = 0
            all_forms = []
            try:
                db = getattr(State.bot, "db", None)
                if db is not None:
                    col_rr = getattr(db, "reactions", None)
                    if not col_rr and hasattr(db, "db"): col_rr = db.db["reactions"]
                    if col_rr is not None:
                        rr_count = await col_rr.count_documents({"guild_id": gid_str})
                    
                    col_form = getattr(db, "forms", None)
                    if not col_form and hasattr(db, "db"): col_form = db.db["forms"]
                    if col_form is not None:
                        cursor = col_form.find({"guild_id": gid_str})
                        all_forms = await cursor.to_list(length=None)
            except Exception as db_err:
                print(f"[DB ERROR] Setting Scan: {db_err}")

            form_configs_by_name = {f.get("embed_name"): f for f in all_forms if f.get("embed_name")}

            # --- [VERIFY HELPERS - REAL-TIME STATUS] ---
            def verify_embed(e_nm):
                """Trả về tên embed nếu tồn tại thực tế, ngược lại trả 'none'"""
                if e_nm and e_nm in embed_data: 
                    return f"`{e_nm}`"
                return f"`none`"

            def parse_module(module_key):
                data = greet_full.get(module_key, {})
                c_id, e_nm, msg = data.get("channel_id"), data.get("embed_name"), data.get("message")
                status = f"`ON`" if (c_id or e_nm or msg) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", verify_embed(e_nm), f"`có`" if msg else f"`none`"

            def parse_booster():
                c_id, e_nm, msg, r_id = boost_cfg.get("channel"), boost_cfg.get("embed"), boost_cfg.get("message"), boost_cfg.get("booster_role")
                status = f"`ON`" if (c_id or e_nm or msg or r_id) else f"`OFF`"
                return status, f"<#{c_id}>" if c_id else f"`none`", verify_embed(e_nm), f"`có`" if msg else f"`none`", f"<@&{r_id}>" if r_id else f"`none`"

            # --- [RÁP GIAO DIỆN FORM ĐỘNG] ---
            hoan_chinh_count = sum(1 for f_name in linked_form_names if form_configs_by_name.get(f_name, {}).get("log_channel_id") and len(form_configs_by_name.get(f_name, {}).get("fields", {})) > 0)
            f_st = f"`ON`" if linked_form_names else f"`OFF`"
            form_section_lines = [f"• **form (tuỳ chọn)**: {f_st}", f"  └ số form hoàn chỉnh: `{hoan_chinh_count}`"]
            
            # [FIX] Tách biến để chống xung đột dấu nháy f-string
            if not linked_form_names:
                form_section_lines.extend(["  └ embed: `none`","  └ số ô nhập liệu: `0`","  └ tiêu đề: `none`","  └ thumbnail: `OFF`","  └ kênh gửi log: `none`"])
            else:
                for f_name in linked_form_names:
                    f_doc = form_configs_by_name.get(f_name, {})
                    
                    embed_val = verify_embed(f_name)
                    field_count = len(f_doc.get('fields', {}))
                    title_val = f_doc.get('form_title') or 'none'
                    thumb_val = '`ON`' if f_doc.get('show_thumbnail') else '`OFF`'
                    
                    log_id = f_doc.get('log_channel_id')
                    log_val = f"<#{log_id}>" if log_id else "none"
                    
                    form_section_lines.extend([
                        f"  └ embed: {embed_val}", 
                        f"  └ số ô nhập liệu: `{field_count}`", 
                        f"  └ tiêu đề: `{title_val}`", 
                        f"  └ thumbnail: {thumb_val}", 
                        f"  └ kênh gửi log: {log_val}"
                    ])
            form_display = "\n".join(form_section_lines)
            
            # --- [RÁP GIAO DIỆN LINK] ---
            lk_st = f"`ON`" if links_by_embed else f"`OFF`"
            link_lines = [f"• **link (đường dẫn)**: {lk_st}"]
            if not links_by_embed:
                link_lines.extend(["  └ embed: `none`","  └ số nút link: `0`","  └ label (nhãn): `none`","  └ url: `none`","  └ emoji: `none`"])
            else:
                for ename, btns in links_by_embed.items():
                    link_lines.append(f"  └ embed `[{ename}]`: số nút link: `{len(btns)}`")
                    for b in btns:
                        link_lines.append(f"    └ {b.get('emoji') or 'none'} `{b.get('label') or 'none'}` → [Link]({b.get('url') or 'none'})")
            link_display = "\n".join(link_lines)

            # --- [TICKET MULTI-STAFF - HIỂN THỊ THỰC TẾ] ---
            t_st = f"`ON`" if ticket_cfg.get("category_id") else f"`OFF`"
            s_roles = ticket_cfg.get("staff_roles", [])
            # Liệt kê đủ tất cả role đã setup
            if isinstance(s_roles, list) and s_roles:
                t_rl = ", ".join([f"<@&{rid}>" for rid in s_roles])
            elif s_roles:
                t_rl = f"<@&{s_roles}>"
            else:
                t_rl = f"`none`"
            
            t_cat = ticket_cfg.get('category_id')
            t_log = ticket_cfg.get('log_channel_id')

            g_st, g_ch, g_eb, g_tx = parse_module("greet")
            l_st, l_ch, l_eb, l_tx = parse_module("leave")
            w_st, w_ch, w_eb, w_tx = parse_module("wellcome")
            b_st, b_ch, b_eb, b_tx, b_rl = parse_booster()
            embed_with_buttons = sum(1 for e in embed_data.values() if isinstance(e, dict) and e.get("buttons"))

            # ================= RÁP DASHBOARD TỔNG (DÀN HÀNG DỌC CHUẨN MẪU) =================
            desc = f"""{Emojis.NO} **hệ thống tiếp tân & tương tác**
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

{Emojis.NO} **kho lưu trữ embed**
• **số embed đã tạo**: `{len(embed_data)}/50`
• **số embed liên kết nút bấm**: `{embed_with_buttons}`
• **reaction role**: `{rr_count}`

{Emojis.NO} **tiện ích button**
• **ticket (hỗ trợ)**: {t_st}
  └ embed: {verify_embed(ticket_cfg.get('embed_name'))}
  └ role hỗ trợ: {t_rl}
  └ danh mục: {f'<#{t_cat}>' if t_cat and str(t_cat) != 'none' else '`none`'}
  └ kênh gửi log: {f'<#{t_log}>' if t_log and str(t_log) != 'none' else '`none`'}
{form_display}
• **identity (giả danh)**:
  └ số vỏ: `{len(ident_data)}`
{link_display}"""

            report = discord.Embed(
                title=f"{Emojis.NO} **chi tiết cấu hình của** {interaction.guild.name}", 
                description=desc, color=0xe6e2dd
            )
            report.set_footer(text="yiyi iu cậu • báo cáo chi tiết linh kiện cloud")
            await interaction.followup.send(embed=report)
        except Exception as e:
            traceback.print_exc()
            try: await interaction.followup.send(f"{Emojis.HOICHAM} yiyi lỗi! `{repr(e)}`", ephemeral=True)
            except: pass

async def setup(bot: commands.Bot):
    bot.tree.add_command(YiyiGroup(bot))
    print("[load] success: commands.fun.yiyi_core (Real-time Dashboard Optimized)", flush=True)
