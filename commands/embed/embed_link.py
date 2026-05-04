import discord
from discord import app_commands
from discord.ext import commands
import re

from core.embed_storage import atomic_update_button, get_all_embed_names
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

# =========================
# LÕI HỆ THỐNG LINK (MAX PING)
# =========================
class EmbedLinkGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="link", description="hệ thống quản lý nút link web đa năng")

    @app_commands.command(name="add", description="gắn một nút link web vào embed")
    @app_commands.describe(
        embed_name="tên embed cần gắn", 
        label="chữ hiển thị trên nút (tối đa 80 ký tự)", 
        url="đường dẫn web (phải bắt đầu bằng http:// hoặc https://)",
        emoji="emoji hiển thị (tùy chọn)"
    )
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def add_link(self, interaction: discord.Interaction, embed_name: str, label: str, url: str, emoji: str = None):
        # Chuyển sang True để bảo mật quá trình setup
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # 1. Validation: Chặn Label quá dài (Discord API giới hạn 80)
        if len(label) > 80:
            return await interaction.followup.send(f"{Emojis.HOICHAM} chữ hiển thị quá dài ({len(label)}/80)! sếp rút gọn lại nhé.")

        # 2. Validation: Regex URL chặt chẽ (Chống khoảng trắng và ký tự lạ)
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, url):
            return await interaction.followup.send(f"{Emojis.HOICHAM} URL không hợp lệ hoặc chứa khoảng trắng. sếp kiểm tra kỹ lại nhé!")

        # 3. Validation: Check Emoji thông minh
        if emoji and not is_valid_emoji(emoji):
            return await interaction.followup.send(f"{Emojis.HOICHAM} emoji không hợp lệ! hãy dùng emoji chuẩn hoặc trong file `emojis.py` nhé.")

        # 4. Tạo Data Nút Link
        btn_data = {
            "type": "link",
            "label": label,
            "url": url.strip(),
            "emoji": emoji
        }
        
        # 5. Cấy nút vào Storage (Tối ưu: Chỉ gọi 1 lần duy nhất)
        # atomic_update_button sẽ tự trả về False nếu không tìm thấy embed
        success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
        
        if success:
            await interaction.followup.send(f"{Emojis.YIYITIM} đã gắn nút link **{label}** vào embed `{embed_name}` thành công!")
        else:
            # IT Pro: Phân tích lỗi dựa trên ngữ cảnh (Embed không tồn tại hoặc đầy nút)
            await interaction.followup.send(f"{Emojis.HOICHAM} không thể gắn nút! có thể embed `{embed_name}` không tồn tại hoặc đã đầy 25 nút.")

    @app_commands.command(name="remove", description="xóa một nút khỏi embed bằng số thứ tự (index)")
    @app_commands.describe(embed_name="tên embed", index="số thứ tự của nút cần xóa (bắt đầu từ 1)")
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def remove_button(self, interaction: discord.Interaction, embed_name: str, index: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # Index của người dùng bắt đầu từ 1, code bắt đầu từ 0
        real_index = index - 1
        
        if real_index < 0:
            return await interaction.followup.send(f"{Emojis.HOICHAM} số thứ tự phải bắt đầu từ 1 chứ sếp!")

        success = await atomic_update_button(guild_id, embed_name, action="remove", index=real_index)
        
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} đã gỡ nút ở vị trí số {index} khỏi embed `{embed_name}`.")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy nút ở vị trí số {index} trong embed `{embed_name}`.")

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
        print("[load] success: commands.embed.embed_link (Hệ Link Max Ping)", flush=True)
    else:
        print("[error] không tìm thấy khung /p để nạp hệ Link!", flush=True)
