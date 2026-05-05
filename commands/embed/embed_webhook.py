import discord
from discord import app_commands
from discord.ext import commands
import copy

from core.embed_storage import load_embed, get_all_embed_names
from core.identity_storage import load_identity, get_all_identity_names
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPERS
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên embed - Cô lập dữ liệu theo từng Server"""
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except Exception: return []

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên 'Vỏ' (Identity) - Cô lập dữ liệu theo từng Server"""
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
    """Dựng hệ thống tương tác (Buttons/Selects) y hệt lệnh /p embed show"""
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    view = discord.ui.View(timeout=None)
    _view_weight = 0
    
    for btn in buttons_data:
        # Tiêm biến số vào từng linh kiện nút bấm
        btn_v = apply_variables(copy.deepcopy(btn), guild, member)
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
                o_v = apply_variables(copy.deepcopy(opt), guild, member)
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
@app_commands.describe(
    name="tên embed muốn dùng",
    identity="chọn 'vỏ' danh tính đã lưu để giả danh"
)
@app_commands.autocomplete(name=embed_name_autocomplete, identity=identity_autocomplete)
async def send_cmd(interaction: discord.Interaction, name: str, identity: str):
    # Sử dụng ephemeral=True để tránh làm phiền member khác trong khi setup
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    channel = interaction.channel

    # 1. TRUY XUẤT DỮ LIỆU
    data = await load_embed(guild.id, name)
    ident_raw = await load_identity(guild.id, identity)

    if not data:
        return await interaction.followup.send(f"{Emojis.HOICHAM} yiyi không tìm thấy embed nào tên `{name}` cả.")
    
    if not ident_raw:
        return await interaction.followup.send(f"{Emojis.HOICHAM} 'vỏ' `{identity}` chưa được đăng ký trong kho.")

    try:
        # --- BƯỚC 2: XỬ LÝ DANH TÍNH (ĐÃ ĐỒNG BỘ LOGIC KIỂM ĐỊNH) ---
        target_name = "yiyi"
        target_avatar = interaction.client.user.display_avatar.url

        # Loại 3: Mượn xác (Target ID)
        if ident_raw.get("type") == "target":
            # Dữ liệu đã được kiểm định và bóc tách sẵn từ lệnh /p identity add
            # Ta lấy trực tiếp để đạt tốc độ phản hồi tối đa
            target_name = ident_raw.get("display_name", "Unknown User")
            target_avatar = ident_raw.get("avatar_url")
            
            # (Optionally) Nếu muốn cập nhật Avatar/Name mới nhất của Target:
            # try:
            #     user = await interaction.client.fetch_user(int(ident_raw["target_id"]))
            #     target_name, target_avatar = user.display_name, user.display_avatar.url
            # except: pass
        
        # Loại 1 & 2: Thủ công hoặc Biến số
        else:
            # IT Pro: Chỉ chạy biến số lên Text/URL để tránh lỗi định dạng Dictionary
            raw_name = ident_raw.get("display_name") or "yiyi"
            raw_avatar = ident_raw.get("avatar_url") or target_avatar
            
            target_name = apply_variables(raw_name, guild, interaction.user)
            target_avatar = apply_variables(raw_avatar, guild, interaction.user)

        # --- BƯỚC 3: CHUẨN BỊ NỘI DUNG ---
        data_v = apply_variables(copy.deepcopy(data), guild, interaction.user)
        embed = discord.Embed.from_dict(data_v)
        view = build_omni_view(data, guild, interaction.user)

        # --- BƯỚC 4: WEBHOOK POOLING ---
        webhooks = await channel.webhooks()
        webhook = next((wh for wh in webhooks if wh.name == "yiyi_webhook"), None)
        
        if not webhook:
            webhook = await channel.create_webhook(
                name="yiyi_webhook", 
                reason="Hệ thống giả danh Identity (Max Ping Edition)"
            )

        # --- BƯỚC 5: EXECUTE ---
        await webhook.send(
            embed=embed,
            view=view,
            username=str(target_name)[:80],
            avatar_url=target_avatar,
            wait=True
        )

        await interaction.followup.send(f"{Emojis.YIYITIM} Đã mượn xác **{identity}** để gửi embed `{name}` thành công!")

    except discord.Forbidden:
        await interaction.followup.send(f"{Emojis.HOICHAM} Yiyi thiếu quyền 'Quản lý Webhook' tại kênh này.")
    except Exception as e:
        print(f"[Identity Error] Guild: {guild.id} | {e}")
        await interaction.followup.send(f"{Emojis.HOICHAM} Có lỗi kỹ thuật khi thực hiện 'biến hình'.")

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
        if embed_group:
            # Dọn dẹp lệnh cũ để đảm bảo tính nhất quán sau khi nâng cấp
            existing = next((c for c in embed_group.commands if c.name == "send"), None)
            if existing: embed_group.remove_command("send")
            
            embed_group.add_command(send_cmd)
            print("[load] success: embed_webhook (Identity Synced Edition)", flush=True)
