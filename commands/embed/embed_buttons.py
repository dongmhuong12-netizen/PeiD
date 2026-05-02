import discord
from discord import app_commands
from discord.ext import commands
import re

from core.embed_storage import load_embed, save_embed, get_all_embed_names
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER
# =============================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên embed chuẩn Multi-server (cách ly dữ liệu giữa các guild)"""
    guild = interaction.guild
    if not guild: return []
    names = await get_all_embed_names(guild.id)
    return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]

# =============================
# MODAL: THÊM NÚT BẤM (LINK)
# =============================
class EmbedButtonModal(discord.ui.Modal, title="Cài đặt Nút bấm tương tác"):
    # IT Pro: Giới hạn độ dài label theo tiêu chuẩn Discord (max 80)
    label = discord.ui.TextInput(
        label="Nhãn hiển thị trên nút",
        placeholder="Ví dụ: Tham gia ngay, Group hỗ trợ...",
        min_length=1,
        max_length=80,
        required=True
    )
    url = discord.ui.TextInput(
        label="Đường dẫn Link (URL)",
        placeholder="https://discord.gg/peid-community",
        required=True
    )

    def __init__(self, embed_name: str):
        super().__init__()
        self.embed_name = embed_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Regex Validation: Kiểm tra URL chuẩn IT
        url_pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        if not re.match(url_pattern, self.url.value):
            return await interaction.followup.send(f"{Emojis.HOICHAM} URL không hợp lệ! Hãy bắt đầu bằng `http://` hoặc `https://` nhé.")

        # Truy xuất dữ liệu từ kho (Multi-guild context)
        data = await load_embed(interaction.guild.id, self.embed_name)
        if not data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy embed `{self.embed_name}` trong hệ thống.")

        # Cấu trúc lưu trữ Buttons (Chuẩn bị sẵn móng cho việc hỗ trợ nhiều nút sau này)
        # Hiện tại hỗ trợ 1 nút Link chính cho Phase 3
        data["buttons"] = [
            {
                "type": "link",
                "label": self.label.value,
                "url": self.url.value
            }
        ]
        
        # Lưu lại bản ghi đã cập nhật
        await save_embed(interaction.guild.id, self.embed_name, data)
        
        # Phản hồi thành công (Văn phong Yiyi)
        embed_success = discord.Embed(
            title=f"{Emojis.YIYITIM} Đã gắn nút thành công!",
            description=(
                f"Embed `{self.embed_name}` hiện đã được trang bị nút bấm mới:\n"
                f"• **Nhãn:** `{self.label.value}`\n"
                f"• **Link:** [Nhấn để xem]({self.url.value})\n\n"
                f"Sếp có thể dùng `/p embed show` hoặc `/p embed send` để xem thành quả nhé!"
            ),
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_success)

# =============================
# COMMAND: BUTTON (SUB-COMMAND)
# =============================

@app_commands.command(name="button", description="gắn nút bấm tương tác (link/url) vào embed hiện có")
@app_commands.describe(name="tên embed muốn gắn nút")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def button_cmd(interaction: discord.Interaction, name: str):
    # Kiểm tra quyền hạn (Chỉ Admin mới được cấu hình hệ thống)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} Quyền trượng của sếp chưa đủ để dùng lệnh này đâu!", ephemeral=True)
        
    data = await load_embed(interaction.guild.id, name)
    if not data:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} Yiyi không tìm thấy embed mang tên `{name}`.", ephemeral=True)
    
    # Hiển thị Modal để nhập thông tin
    await interaction.response.send_modal(EmbedButtonModal(name))

# =============================
# INJECTION LOGIC (Hệ thống tiêm lệnh chuyên dụng)
# =============================
async def setup(bot: commands.Bot):
    # Tìm kiếm lệnh gốc /p
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Truy cập vào phân nhánh 'embed'
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
                
        if embed_group:
            # Gỡ bỏ lệnh button cũ (nếu có) để tránh xung đột Sharding/Reload
            existing = next((c for c in embed_group.commands if c.name == "button"), None)
            if existing: 
                embed_group.remove_command("button")
            
            # Tiêm lệnh mới vào cây lệnh
            embed_group.add_command(button_cmd)
            print("[load] success: commands.embed.embed_buttons (Phase 3 IT-Ready)", flush=True)
        else:
            print("[error] Phase 3: Không tìm thấy nhánh /p embed để tiêm lệnh button.", flush=True)
    else:
        print("[error] Phase 3: Khung lệnh /p chưa tồn tại. Hãy nạp core.root trước.", flush=True)


