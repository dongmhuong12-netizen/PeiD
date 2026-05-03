import discord
from discord import app_commands
from discord.ext import commands
import re

from core.embed_storage import load_embed, atomic_update_button, get_all_embed_names
from utils.emojis import Emojis

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
# LÕI HỆ THỐNG LINK
# =========================
class EmbedLinkGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="link", description="hệ thống quản lý nút link web đa năng")

    @app_commands.command(name="add", description="gắn một nút link web vào embed")
    @app_commands.describe(
        embed_name="tên embed cần gắn", 
        label="chữ hiển thị trên nút", 
        url="đường dẫn web (phải có http:// hoặc https://)",
        emoji="emoji hiển thị (tùy chọn)"
    )
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def add_link(self, interaction: discord.Interaction, embed_name: str, label: str, url: str, emoji: str = None):
        await interaction.response.defer(ephemeral=False)
        guild_id = interaction.guild.id
        
        # 1. Validation: Kiểm tra embed
        embed_data = await load_embed(guild_id, embed_name)
        if not embed_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} aree... không tìm thấy embed `{embed_name}`. hãy kiểm tra lại nhé!")

        # 2. Validation: Ép chuẩn URL (Tránh lỗi API Discord từ chối link sai định dạng)
        if not re.match(r"^https?://", url):
            return await interaction.followup.send(f"{Emojis.HOICHAM} đường dẫn URL không hợp lệ! sếp phải bắt đầu bằng `http://` hoặc `https://` nhé.")

        # 3. Tạo Data Nút Link thuần túy (Không có custom_id để tránh dính líu đến Event Listener)
        btn_data = {
            "type": "link",
            "label": label,
            "url": url,
            "emoji": emoji
        }
        
        # 4. Cấy nút vào Storage
        success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
        
        if success:
            msg = f"{Emojis.YIYITIM} đã gắn nút link **{label}** vào embed `{embed_name}` thành công!"
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} embed này đã đầy giới hạn 25 nút bấm, không thể nhét thêm được nữa.")

    @app_commands.command(name="remove", description="xóa một nút khỏi embed bằng số thứ tự (index)")
    @app_commands.describe(embed_name="tên embed", index="số thứ tự của nút cần xóa (bắt đầu từ 1)")
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def remove_button(self, interaction: discord.Interaction, embed_name: str, index: int):
        await interaction.response.defer(ephemeral=False)
        guild_id = interaction.guild.id
        
        # Index của người dùng bắt đầu từ 1, code bắt đầu từ 0
        real_index = index - 1
        
        success = await atomic_update_button(guild_id, embed_name, action="remove", index=real_index)
        
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} đã gỡ nút ở vị trí số {index} khỏi embed `{embed_name}`.")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy nút ở vị trí số {index}. sếp đếm lại xem đúng chưa nhé!")

# =========================
# INJECTION
# =========================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn dẹp lệnh cũ nếu lỡ bị kẹt
        existing = next((c for c in p_cmd.commands if c.name == "link"), None)
        if existing: p_cmd.remove_command("link")
        
        p_cmd.add_command(EmbedLinkGroup())
        print("[load] success: commands.embed.embed_link (Hệ Web Link)", flush=True)
    else:
        print("[error] không tìm thấy khung /p!", flush=True)


