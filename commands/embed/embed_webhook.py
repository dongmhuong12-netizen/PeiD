import discord
from discord import app_commands
from discord.ext import commands
import copy

from core.embed_storage import load_embed, get_all_embed_names
from core.identity_storage import load_identity, get_all_identity_names
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# HELPER: XỬ LÝ BIẾN SỐ ĐA TẦNG (FIX LỖI KỸ THUẬT)
# =============================

def process_variable_data(target, guild, member):
    """
    IT PRO: Đệ quy để dịch biến số trong mọi ngóc ngách của Embed/Button
    Đảm bảo không làm hỏng cấu trúc Dictionary của Discord.
    """
    if isinstance(target, str):
        # Nếu là chuỗi, tiến hành dịch biến số (user_name -> Nguyệt)
        return apply_variables(target, guild, member)
    elif isinstance(target, list):
        # Nếu là danh sách (như các field), duyệt từng phần tử
        return [process_variable_data(item, guild, member) for item in target]
    elif isinstance(target, dict):
        # Nếu là Dictionary (như nội dung Embed), duyệt từng key-value
        return {k: process_variable_data(v, guild, member) for k, v in target.items()}
    # Nếu là số hoặc None, giữ nguyên
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
# OMNI-INTERACTION VIEW BUILDER
# =============================

def build_omni_view(data, guild, member):
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    view = discord.ui.View(timeout=None)
    _view_weight = 0
    
    for btn in buttons_data:
        # Sử dụng hàm xử lý biến số an toàn cho từng nút bấm
        btn_v = process_variable_data(copy.deepcopy(btn), guild, member)
        btype = btn_v.get("type")
        _w = 5 if btype == "select" else 1
        
        if _view_weight + _w > 25: continue
        _view_weight += _w

        if btype == "link":
            view.add_item(discord.ui.Button(
                label=btn_v.get("label", "Link"), 
                url=btn_v.get("url"), 
                emoji=btn_v.get("emoji")
            ))
        elif btype == "button":
            style_val = btn_v.get("style", 1)
            style = discord.ButtonStyle(style_val) if 1 <= style_val <= 4 else discord.ButtonStyle.primary
            view.add_item(discord.ui.Button(
                style=style, label=btn_v.get("label"), 
                custom_id=btn_v.get("custom_id"), emoji=btn_v.get("emoji")
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
# WEBHOOK COMMAND (SEND)
# =============================

@app_commands.command(name="send", description="gửi embed vào kênh hiện tại bằng danh tính giả (identity)")
@app_commands.describe(name="tên embed muốn dùng", identity="chọn 'vỏ' danh tính đã lưu")
@app_commands.autocomplete(name=embed_name_autocomplete, identity=identity_autocomplete)
async def send_cmd(interaction: discord.Interaction, name: str, identity: str):
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    channel = interaction.channel

    data = await load_embed(guild.id, name)
    ident_raw = await load_identity(guild.id, identity)

    if not data or not ident_raw:
        return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy dữ liệu yêu cầu.")

    try:
        # --- BƯỚC 2: XỬ LÝ DANH TÍNH ---
        target_name = "yiyi"
        target_avatar = interaction.client.user.display_avatar.url

        if ident_raw.get("type") == "target":
            target_name = ident_raw.get("display_name", "Unknown")
            target_avatar = ident_raw.get("avatar_url")
        else:
            # Dịch biến số cho Tên và Avatar của "Vỏ"
            target_name = apply_variables(ident_raw.get("display_name", "yiyi"), guild, interaction.user)
            target_avatar = apply_variables(ident_raw.get("avatar_url", target_avatar), guild, interaction.user)

        # --- BƯỚC 3: CHUẨN BỊ NỘI DUNG (SỬ DỤNG HÀM XỬ LÝ ĐA TẦNG) ---
        # Đây là nơi fix lỗi "biến hình" cho cả Embed
        data_v = process_variable_data(copy.deepcopy(data), guild, interaction.user)
        
        # Tạo Embed từ dict đã được dịch sạch biến số
        embed = discord.Embed.from_dict(data_v)
        view = build_omni_view(data, guild, interaction.user)

        # --- BƯỚC 4: WEBHOOK POOLING ---
        webhooks = await channel.webhooks()
        webhook = next((wh for wh in webhooks if wh.name == "yiyi_webhook"), None)
        if not webhook:
            webhook = await channel.create_webhook(name="yiyi_webhook", reason="Identity System")

        # --- BƯỚC 5: PHÓNG ---
        await webhook.send(
            embed=embed, view=view,
            username=str(target_name)[:80],
            avatar_url=target_avatar,
            wait=True
        )

        await interaction.followup.send(f"{Emojis.YIYITIM} Đã mượn xác **{identity}** gửi embed `{name}` thành công!")

    except Exception as e:
        print(f"[Send Error] {e}")
        await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi kỹ thuật: `{str(e)}`")

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
            print("[load] success: embed_webhook (Clean Variable Edition)", flush=True)
