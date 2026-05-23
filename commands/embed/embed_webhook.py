import discord
from discord import app_commands
from discord.ext import commands
import copy
import re

from core.embed_storage import load_embed, get_all_embed_names
from core.identity_storage import load_identity, get_all_identity_names
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# HELPER: XỬ LÝ BIẾN SỐ ĐA TẦNG (BẢO TOÀN LOGIC)
# =============================

def process_variable_data(target, guild, member):
    """Đệ quy dịch biến số trong Embed/Button/Select để cá nhân hóa tối đa"""
    if isinstance(target, str):
        return apply_variables(target, guild, member)
    elif isinstance(target, list):
        return [process_variable_data(item, guild, member) for item in target]
    elif isinstance(target, dict):
        return {k: process_variable_data(v, guild, member) for k, v in target.items()}
    return target

# =============================
# AUTOCOMPLETE HELPERS
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except Exception: return []

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_identity_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except Exception: return []

# =============================
# OMNI-INTERACTION VIEW BUILDER (INDUSTRIAL FIX)
# =============================

def build_omni_view(data, guild, member):
    """Dựng hệ thống nút bấm với mạch giãn cách thẩm mỹ"""
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    view = discord.ui.View(timeout=None)
    _view_weight = 0
    
    for btn in buttons_data:
        btn_v = process_variable_data(copy.deepcopy(btn), guild, member)
        btype = btn_v.get("type")
        _w = 5 if btype == "select" else 1
        
        if _view_weight + _w > 25: continue
        _view_weight += _w

        # [THẨM MỸ INDUSTRIAL] Tự động nới lỏng khoảng cách cho Label
        raw_label = btn_v.get("label", "")
        formatted_label = f" {raw_label.strip()} " if raw_label else None

        if btype == "link":
            view.add_item(discord.ui.Button(
                label=formatted_label or "Link", 
                url=btn_v.get("url"), 
                emoji=btn_v.get("emoji")
            ))
        elif btype == "button":
            style_val = btn_v.get("style", 1)
            style = discord.ButtonStyle(style_val) if 1 <= style_val <= 4 else discord.ButtonStyle.primary
            view.add_item(discord.ui.Button(
                style=style, 
                label=formatted_label or "Button", 
                custom_id=btn_v.get("custom_id"), 
                emoji=btn_v.get("emoji")
            ))
        elif btype == "select":
            opts = []
            for opt in btn_v.get("options", []):
                o_v = process_variable_data(copy.deepcopy(opt), guild, member)
                opts.append(discord.SelectOption(
                    label=str(o_v.get("label"))[:100], 
                    value=str(o_v.get("value")), 
                    description=str(o_v.get("description", ""))[:100], 
                    emoji=o_v.get("emoji")
                ))
            if opts:
                view.add_item(discord.ui.Select(
                    custom_id=btn_v.get("custom_id"), 
                    placeholder=str(btn_v.get("placeholder", "Chọn..."))[:150], 
                    options=opts
                ))
    return view

# =============================
# OPTIMIZED SEND COMMAND (NO-CHANNEL VERSION)
# =============================

@app_commands.command(name="send", description="gửi embed vào kênh hiện tại (có thể giả danh)")
@app_commands.describe(
    name="chọn embed chính muốn gửi", 
    identity="chọn vỏ danh tính để giả danh (tùy chọn)",
    extra_embeds="nhập tên các embed khác, cách nhau bằng dấu phẩy (vd: b, c)"
)
@app_commands.autocomplete(name=embed_name_autocomplete, identity=identity_autocomplete)
async def send_cmd(interaction: discord.Interaction, name: str, identity: str = None, extra_embeds: str = None):
    # Phản hồi Ephemeral=True để không làm rác kênh chat khi sếp điều khiển
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    target_channel = interaction.channel # Cố định kênh hiện tại giống logic show

    # [KẾT NỐI MẠCH] Gom danh sách các embed cần gửi lần lượt
    embed_names = [name]
    if extra_embeds:
        embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])

    # Bắt đầu vòng lặp xử lý liên thanh
    for emb_name in embed_names:
        # 1. Tải dữ liệu Embed (DEF)
        data = await load_embed(guild.id, emb_name)
        if not data:
            await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{emb_name}` trong kho.")
            continue # Bỏ qua embed lỗi, tiếp tục bắn embed tiếp theo

        try:
            # 2. Xử lý nội dung & linh kiện (ATK)
            data_v = process_variable_data(copy.deepcopy(data), guild, interaction.user)
            embed = discord.Embed.from_dict(data_v)
            view = build_omni_view(data, guild, interaction.user)

            # --- NHÁNH 1: GỬI QUA IDENTITY (WEBHOOK) ---
            if identity:
                ident_raw = await load_identity(guild.id, identity)
                if not ident_raw:
                    await interaction.followup.send(f"{Emojis.HOICHAM} danh tính `{identity}` không tồn tại.")
                    continue

                if not target_channel.permissions_for(guild.me).manage_webhooks:
                    await interaction.followup.send(f"{Emojis.HOICHAM} yiyi thiếu quyền `Manage Webhooks` để giả danh.")
                    continue

                target_name = apply_variables(ident_raw.get("display_name", "yiyi"), guild, interaction.user)
                target_avatar = apply_variables(ident_raw.get("avatar_url"), guild, interaction.user)

                webhooks = await target_channel.webhooks()
                webhook = next((wh for wh in webhooks if wh.name == "yiyi_webhook"), None)
                if not webhook:
                    webhook = await target_channel.create_webhook(name="yiyi_webhook", reason="Identity System")

                # Chuẩn bị phóng
                send_params = {
                    "embed": embed,
                    "username": str(target_name)[:80],
                    "avatar_url": target_avatar,
                    "wait": True
                }
                if view: send_params["view"] = view
                
                await webhook.send(**send_params)

            # --- NHÁNH 2: GỬI TRỰC TIẾP (BOT) ---
            else:
                if not target_channel.permissions_for(guild.me).send_messages:
                    await interaction.followup.send(f"{Emojis.HOICHAM} yiyi không có quyền gửi tin nhắn ở đây.")
                    continue

                await target_channel.send(embed=embed, view=view)

        except Exception as e:
            print(f"[Send Error] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi kỹ thuật khi gửi `{emb_name}`: `{str(e)}`")

    # 3. Chốt sổ thành công (Dấu vết chỉ sếp thấy)
    if len(embed_names) > 1:
        await interaction.followup.send(f"{Emojis.BUOMA} gửi đi {len(embed_names)} thành công")
    else:
        await interaction.followup.send(f"{Emojis.BUOMA} embed `{name}` gửi đi thành công.")

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
        if embed_group:
            existing = next((c for c in embed_group.commands if c.name == "send"), None)
            if existing: embed_group.remove_command("send")
            
            embed_group.add_command(send_cmd)
            print("[load] success: embed_webhook (Show-Like Edition + Multi-Embed)", flush=True)
