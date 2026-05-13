import discord
from discord import app_commands
from discord.ext import commands
import re

# Nạp công cụ cập nhật nút bấm và trí nhớ Form mới
from core.embed_storage import atomic_update_button, load_embed
from core.forms_storage import update_form_base, update_form_field # [CẤY MỚI]
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
        # QUY TẮC 3S: Defer ngay lập tức (Industrial Standard)
        await interaction.response.defer(ephemeral=True)
        
        # Gọt sạch ID kênh log
        clean_log_id = self._sanitize_id(log_channel_id)
        
        # [CẤY MỚI] Đồng bộ cấu hình nền lên Cloud Atlas
        # Dữ liệu được bóc tách theo từng embed_name để hỗ trợ multi-form
        success = await update_form_base(
            interaction.guild.id, 
            embed_name, 
            form_title, 
            clean_log_id, 
            show_thumbnail
        )
        
        if success:
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
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} có lỗi khi lưu cấu hình form vào Cloud.")

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
        
        # [CẤY MỚI] Đẩy dữ liệu slot vào mảng trường của MongoDB
        success = await update_form_field(
            interaction.guild.id, 
            embed_name, 
            slot, 
            label, 
            placeholder, 
            required
        )

        if success:
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
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi: cậu cần setup đơn trước bằng `/p forms setup`.")

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

        # [GIA CỐ] Kiểm tra sự tồn tại của Embed trước khi gắn nút
        if not await load_embed(interaction.guild.id, embed_name):
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{embed_name}` để liên kết.")

        # Atomic Update đã được nâng cấp lên Async/MongoDB ở file core/embed_storage.py
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
