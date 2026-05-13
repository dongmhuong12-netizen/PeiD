import discord
from discord import app_commands
from discord.ext import commands
import re

from core.embed_storage import atomic_update_button
# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
from utils.emojis import Emojis 

class FormsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="forms", description="Hệ thống biểu mẫu và đơn từ chuyên nghiệp")

    def _sanitize_id(self, input_str: str):
        """[BỘ LỌC YIYI] Gọt sạch tag kênh/role chỉ lấy số ID"""
        if not input_str: return ""
        return re.sub(r'\D', '', input_str)

    # =========================
    # LỆNH 1: SETUP NỀN (Văn phong & Thứ tự mới)
    # =========================
    @app_commands.command(name="setup", description="1. Setup đơn, tiêu đề và kênh nhận kết quả")
    @app_commands.describe(
        embed_name="2. Tên embed gắn form",
        form_title="4. Tiêu đề hiển thị trên đơn",
        log_channel_id="3. ID hoặc tag kênh nhận kết quả",
        show_thumbnail="Lựa chọn hiển thị avatar người gửi (Thumbnail)"
    )
    async def setup_base(self, interaction: discord.Interaction, embed_name: str, form_title: str, log_channel_id: str, show_thumbnail: bool = True):
        await interaction.response.defer(ephemeral=True)
        
        # Gọt sạch ID kênh log
        clean_log_id = self._sanitize_id(log_channel_id)
        
        # [TRÍ NHỚ ĐÃ BÓC TÁCH] 
        # Cậu sẽ thay thế logic lấy và lưu config vào MongoDB tại đây.
        # Logic gọt sạch ID và chuẩn bị dữ liệu phản hồi vẫn giữ nguyên.
        
        # Render văn phong theo ý sếp
        embed_res = discord.Embed(
            title=f"{Emojis.MATTRANG} thiết lập form thành công",
            description=(
                f"embed: `{embed_name}`.\n•\n"
                f"tiêu đề: **{form_title}**\n"
                f"kênh trả đơn: <#{clean_log_id}>"
            ),
            color=0xf8bbd0
        )
            
        await interaction.followup.send(embed=embed_res)

    # =========================
    # LỆNH 2: THIẾT LẬP TRƯỜNG (Văn phong mới)
    # =========================
    @app_commands.command(name="field", description="Cấu hình nội dung cho từng ô nhập liệu (Tối đa 5)")
    @app_commands.choices(slot=[
        app_commands.Choice(name="Trường 1", value=1),
        app_commands.Choice(name="Trường 2", value=2),
        app_commands.Choice(name="Trường 3", value=3),
        app_commands.Choice(name="Trường 4", value=4),
        app_commands.Choice(name="Trường 5", value=5),
    ])
    async def field(self, interaction: discord.Interaction, embed_name: str, slot: int, label: str, placeholder: str = "Nhập nội dung...", required: bool = True):
        await interaction.response.defer(ephemeral=True)
        
        # [TRÍ NHỚ ĐÃ BÓC TÁCH]
        # Xóa bỏ các lệnh gọi _get_config, _save_config và force_save.
        # Dữ liệu slot, label, placeholder sẽ được cấy vào MongoDB sau này.

        # Render văn phong đóng khung biến
        embed_res = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật nội dung trường `{slot}` thành công",
            description=(
                f"embed: `{embed_name}`\n"
                f"nội dung: `{label}`\n"
                f"chú thích: `{placeholder}`"
            ),
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_res)

    # =========================
    # LỆNH 3: CẤY NÚT GỬI ĐƠN (Văn phong mới)
    # =========================
    @app_commands.command(name="apply", description="11. Liên kết Form vào Embed")
    async def apply(self, interaction: discord.Interaction, embed_name: str, label: str = "Gửi đơn đăng ký"):
        await interaction.response.defer(ephemeral=True)
        
        btn_data = {
            "type": "button",
            "style": "success",
            "label": label,
            "emoji": "📝",
            "custom_id": f"yiyi:forms:open:{embed_name}", 
            "system": "forms"
        }

        # [GIA CỐ] Giữ lại atomic_update_button vì đây là DAL (Data Access Layer) 
        # sẽ được cậu xử lý MongoDB bên trong core/embed_storage.py sau.
        success = await atomic_update_button(interaction.guild.id, embed_name, action="add", button_data=btn_data)
        
        if success:
            embed_success = discord.Embed(
                title=f"{Emojis.MATTRANG} liên kết với embed `{embed_name}` thành công",
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_success)
        else:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm...? có lỗi gì đó ở đây",
                description=f"cậu hãy nhập lại tên embed hoặc kiểm tra lại trường nhập liệu nhé",
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_err)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "forms"), None)
        if existing: p_cmd.remove_command("forms")
        p_cmd.add_command(FormsGroup())
        print("[LOAD] Success: commands.forms.forms_group (Stylized)", flush=True)
