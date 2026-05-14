import discord
from discord import app_commands
from discord.ext import commands
import re

# IT Pro: Bổ sung load_embed để phục vụ logic gợi ý nút bấm
from core.embed_storage import load_embed, atomic_update_button, get_all_embed_names
from utils.emojis import Emojis

# =========================
# HELPER: VALIDATION IT PRO
# =========================

def is_valid_emoji(emoji_str: str) -> bool:
    """Kiểm tra emoji có nằm trong bộ Emojis.py hoặc định dạng Discord hợp lệ không"""
    if not emoji_str: return True
    # Kiểm tra trong bộ emoji sếp đã định nghĩa
    system_emojis = [Emojis.HOICHAM, Emojis.MATTRANG, Emojis.YIYITIM]
    if emoji_str in system_emojis: return True
    
    # Check định dạng Custom Emoji <:name:id> hoặc Unicode cơ bản
    custom_emoji_pattern = r"^<a?:\w+:\d+>$"
    # Các emoji unicode thường có độ dài ngắn, check đơn giản bằng length hoặc regex
    return bool(re.match(custom_emoji_pattern, emoji_str)) or len(emoji_str) <= 4

# =========================
# HELPER: AUTOCOMPLETE
# =========================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên embed thần tốc"""
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        choices = [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
        return choices
    except Exception:
        return []

# [GIA CỐ] Gợi ý danh sách nút bấm hiện có để gỡ chính xác theo ý cậu
async def button_index_autocomplete(interaction: discord.Interaction, current: str):
    """Tự động liệt kê danh sách nút bấm dựa trên embed_name đã chọn"""
    embed_name = interaction.namespace.embed_name
    if not embed_name: return []
    
    guild_id = interaction.guild.id
    data = await load_embed(guild_id, embed_name)
    
    if not data or "buttons" not in data or not data["buttons"]:
        return []

    choices = []
    for i, btn in enumerate(data["buttons"]):
        label = btn.get("label", "Không tiêu đề")
        btn_type = btn.get("type", "link")
        # Format: "1. Tên nút (link)"
        choice_display = f"{i + 1}. {label} ({btn_type})"
        
        if current.lower() in choice_display.lower():
            choices.append(app_commands.Choice(name=choice_display, value=i + 1))
            
    return choices[:25]

# =========================
# LÕI HỆ THỐNG LINK (MAX PING)
# =========================
class EmbedLinkGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="link", description="hệ thống quản lý nút link web đa năng")

    @app_commands.command(name="add", description="gắn một nút link web vào embed")
    @app_commands.describe(
        embed_name="tên embed cần gắn", 
        label="nhãn nút (hỗ trợ cả emoji thiết bị và discord, tối đa 80 ký tự)", 
        url="đường dẫn web (phải bắt đầu bằng http:// hoặc https://)"
    )
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def add_link(self, interaction: discord.Interaction, embed_name: str, label: str, url: str):
        # Chuyển sang True để bảo mật quá trình setup
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # 1. Validation: Chặn Label quá dài
        if len(label) > 80:
            return await interaction.followup.send(f"{Emojis.HOICHAM} chữ hiển thị vượt giới hạn ({len(label)}/80). hãy viết ngắn đi một chút nhé.")

        # 2. Validation: Regex URL chặt chẽ
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, url):
            return await interaction.followup.send(f"{Emojis.HOICHAM} aree... URL cậu nhập có vẻ không đúng định dạng rồi. cậu hãy chắc chắn nó bắt đầu bằng http:// hoặc https:// nhé.")

        # [CẬP NHẬT GIAO DIỆN CHUẨN INDUSTRIAL] Tự động nới lỏng khoảng cách cho Emoji và Icon Link
        formatted_label = f" {label.strip()} "

        # 3. Tạo Data Nút Link (Tích hợp vạn năng: Emoji đã nằm trong Label)
        btn_data = {
            "type": "link",
            "label": formatted_label,
            "url": url.strip(),
            "emoji": None # Đã tích hợp vào Label nên field này để None
        }
        
        # 4. Cấy nút vào Storage (Mạch Append chuẩn Multi-Link)
        success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
        
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} liên kết Link **{label}** với Embed `{embed_name}` thành công. có thể dùng `/p embed show` để sử dụng nhé.")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} aree...? embed {embed_name} đã đạt giới hạn 25 nút bấm hoặc không tồn tại. cậu hãy kiểm tra lại nhé.")

    @app_commands.command(name="remove", description="xóa một nút khỏi embed bằng số thứ tự (index)")
    @app_commands.describe(embed_name="tên embed", index="chọn nút cần xóa từ danh sách gợi ý")
    @app_commands.autocomplete(embed_name=embed_name_autocomplete, index=button_index_autocomplete)
    async def remove_button(self, interaction: discord.Interaction, embed_name: str, index: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # Index của người dùng bắt đầu từ 1, code bắt đầu từ 0
        real_index = index - 1
        
        if real_index < 0:
            return await interaction.followup.send(f"{Emojis.HOICHAM} số thứ tự phải bắt đầu từ 1 chứ cậu!")

        success = await atomic_update_button(guild_id, embed_name, action="remove", index=real_index)
        
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} gỡ nút vị trí **{index}** thành công. các nút phía sau đã tự động dồn lại thay thế vị trí đã xoá.")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} aree...? **yiyi** không tìm thấy nút nào ở vị trí số {index} cả. cậu hãy chọn theo danh sách gợi ý của **yiyi** cho chính xác nhé.")

# =========================
# INJECTION
# =========================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn dẹp lệnh cũ để tránh trùng lặp khi reload
        existing = next((c for c in p_cmd.commands if c.name == "link"), None)
        if existing: p_cmd.remove_command("link")
        
        p_cmd.add_command(EmbedLinkGroup())
        print("[load] success: commands.embed.embed_link (Universal Label & Industrial Fix)", flush=True)
    else:
        print("[error] không tìm thấy khung /p!", flush=True)
