import discord
from discord import app_commands
from discord.ext import commands
import re

from core.embed_storage import load_embed, get_all_embed_names
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER
# =============================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên embed dựa trên ID server hiện tại (Multi-server isolation)"""
    guild = interaction.guild
    if not guild: return []
    names = await get_all_embed_names(guild.id)
    return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]

# [BỔ SUNG PHASE 3] Hàm tạo View nút bấm từ dữ liệu lưu trữ cho Webhook
def create_embed_view(data):
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    view = discord.ui.View()
    for btn in buttons_data:
        if btn.get("type") == "link":
            view.add_item(discord.ui.Button(label=btn["label"], url=btn["url"]))
    return view

# =============================
# WEBHOOK COMMAND (SEND)
# =============================

@app_commands.command(name="send", description="gửi embed vào kênh bằng webhook (giả danh người gửi)")
@app_commands.describe(
    name="tên embed muốn dùng",
    channel="kênh để gửi embed",
    username="tên hiển thị của người gửi (tùy chọn)",
    avatar_url="link ảnh làm avatar của người gửi (tùy chọn)"
)
@app_commands.autocomplete(name=embed_name_autocomplete)
async def send_cmd(
    interaction: discord.Interaction, 
    name: str, 
    channel: discord.TextChannel,
    username: str = None,
    avatar_url: str = None
):
    # Sử dụng ephemeral=True để tránh rác kênh khi admin đang thao tác
    await interaction.response.defer(ephemeral=True)
    
    # 1. TRÍ NHỚ ĐA MÁY CHỦ: Lấy dữ liệu từ kho theo guild_id
    data = await load_embed(interaction.guild.id, name)
    if not data:
        return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed có tên `{name}`, hãy thử nhập lại nhé")

    # Tái tạo Embed từ dữ liệu JSON
    embed = discord.Embed.from_dict(data)
    
    # [CẬP NHẬT PHASE 3] Kiểm tra và tạo View chứa nút bấm
    view = create_embed_view(data)

    try:
        # 2. QUẢN LÝ WEBHOOK TỐI ƯU (Pooling Logic)
        # Kiểm tra xem kênh có webhook nào mang tên định danh của yiyi chưa
        webhooks = await channel.webhooks()
        webhook = next((wh for wh in webhooks if wh.name == "yiyi_webhook"), None)
        
        # Nếu chưa có thì tạo mới (lưu vết bằng reason để admin server biết nguồn gốc)
        if not webhook:
            webhook = await channel.create_webhook(name="yiyi_webhook", reason=f"Hệ thống Webhook của yiyi cho server {interaction.guild.name}")

        # 3. OVERRIDE IDENTITY (Tính năng 'điếm thúi' của Webhook)
        # Gửi embed với danh tính giả và đính kèm View (nút bấm) nếu có
        await webhook.send(
            embed=embed,
            view=view,
            username=username or "yiyi",
            avatar_url=avatar_url or interaction.client.user.display_avatar.url,
            wait=True # Chờ phản hồi từ Discord để xác nhận gửi thành công
        )

        await interaction.followup.send(f"{Emojis.YIYITIM} Đã 'giả danh' và gửi thành công embed `{name}` vào {channel.mention}!")

    except discord.Forbidden:
        await interaction.followup.send(f"{Emojis.HOICHAM} Yiyi thiếu quyền 'Quản lý Webhook' tại kênh được chọn.")
    except discord.HTTPException as e:
        await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi API Discord: {e.text}")
    except Exception as e:
        print(f"[Phase 2 Error] Guild: {interaction.guild.id} | {e}")
        await interaction.followup.send(f"{Emojis.HOICHAM} Có lỗi kỹ thuật xảy ra khi gửi Webhook.")

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Truy cập vào group 'embed' nằm trong group 'p'
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
                
        if embed_group:
            # Dọn dẹp lệnh 'send' cũ nếu có để tránh xung đột Sharding
            existing = next((c for c in embed_group.commands if c.name == "send"), None)
            if existing: embed_group.remove_command("send")
            
            # Tiêm lệnh Webhook vào cây lệnh chính
            embed_group.add_command(send_cmd)
            print("[load] success: commands.embed.embed_webhook (Phase 2 Multi-Ready)", flush=True)
        else:
            print("[error] Phase 2: Không tìm thấy group /p embed để tích hợp.", flush=True)


