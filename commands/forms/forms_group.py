import discord
from discord import app_commands
from discord.ext import commands
import re
import traceback

# Nạp công cụ cập nhật nút bấm và trí nhớ Form mới
from core.embed_storage import atomic_update_button, load_embed, get_all_embed_names
from core.forms_storage import update_form_base, update_form_field, get_all_forms # [GIA CỐ]
from utils.emojis import Emojis 

# =============================
# HELPERS (Bổ trợ) - GIỮ NGUYÊN 100% DNA CỦA NGUYỆT
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    [NÂNG CẤP INDUSTRIAL]
    Autocomplete thần tốc hỗ trợ sếp tìm embed để gắn Form nhanh nhất.
    """
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        choices = [
            app_commands.Choice(name=name, value=name) 
            for name in names if current.lower() in name.lower()
        ][:25]
        return choices
    except Exception:
        return []

class FormsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="forms", description="Hệ thống biểu mẫu và đơn từ chuyên nghiệp")

    def _sanitize_id(self, input_str: str):
        """[BỘ LỌC YIYI] Gọt sạch tag kênh/role chỉ lấy số ID"""
        if not input_str: return ""
        return re.sub(r'\D', '', input_str)

    # =========================
    # LỆNH 1: SETUP NỀN (Fix Treo & Chuẩn hóa logic Thumbnail)
    # =========================
    @app_commands.command(name="setup", description="1. Setup đơn, tiêu đề và kênh nhận kết quả")
    @app_commands.describe(
        embed_name="2. Tên embed gắn form",
        form_title="4. Tiêu đề hiển thị trên đơn",
        log_channel_id="3. ID hoặc tag kênh nhận kết quả",
        show_thumbnail="Lựa chọn hiển thị Avatar người gửi vào Đơn (kênh log)"
    )
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def setup_base(self, interaction: discord.Interaction, embed_name: str, form_title: str, log_channel_id: str, show_thumbnail: bool = True):
        await interaction.response.defer(ephemeral=True)
        try:
            # Gọt sạch ID kênh log
            clean_log_id = self._sanitize_id(log_channel_id)
            if not clean_log_id:
                return await interaction.followup.send(f"{Emojis.HOICHAM} ID kênh trả đơn không hợp lệ.")
            
            # Đồng bộ cấu hình nền lên Cloud Atlas
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
                        f"• embed: `{embed_name}`\n"
                        f"• tiêu đề: **{form_title}**\n"
                        f"• kênh trả đơn: <#{clean_log_id}>\n"
                        f"• hiện avatar lên đơn log: `{'Có' if show_thumbnail else 'Không'}`"
                    ),
                    color=0xf8bbd0
                )
                await interaction.followup.send(embed=embed_res)
            else:
                await interaction.followup.send(f"{Emojis.HOICHAM} có lỗi khi lưu cấu hình form vào Cloud.")
        except Exception as e:
            # [ANTI-HANG]: Chặn đứng việc Discord bị treo vô tận nếu Database lỗi
            print(f"[LỖI FORM SETUP] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi hệ thống khi thiết lập: `{e}`. Hãy kiểm tra Database.")

    # =========================
    # LỆNH 2: THIẾT LẬP TRƯỜNG (Fix Treo)
    # =========================
    @app_commands.command(name="field", description="Cấu hình nội dung cho từng ô nhập liệu (Tối đa 5)")
    @app_commands.describe(embed_name="Tên embed chứa form muốn cấu hình trường")
    @app_commands.choices(slot=[
        app_commands.Choice(name="Trường 1", value=1),
        app_commands.Choice(name="Trường 2", value=2),
        app_commands.Choice(name="Trường 3", value=3),
        app_commands.Choice(name="Trường 4", value=4),
        app_commands.Choice(name="Trường 5", value=5),
    ])
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def field(self, interaction: discord.Interaction, embed_name: str, slot: int, label: str, placeholder: str = "Nhập nội dung...", required: bool = True):
        await interaction.response.defer(ephemeral=True)
        try:
            # Đẩy dữ liệu slot vào mảng trường của MongoDB
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
                        f"• embed: `{embed_name}`\n"
                        f"• nội dung: `{label}`\n"
                        f"• chú thích: `{placeholder}`\n"
                        f"• bắt buộc điền: `{'Có' if required else 'Không'}`"
                    ),
                    color=0xf8bbd0
                )
                await interaction.followup.send(embed=embed_res)
            else:
                await interaction.followup.send(f"{Emojis.HOICHAM} lỗi: cậu cần setup đơn trước bằng `/p forms setup`.")
        except Exception as e:
            print(f"[LỖI FORM FIELD] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi hệ thống khi cấu hình trường: `{e}`")

    # =========================
    # LỆNH 3: CẤY NÚT GỬI ĐƠN (Gỡ bom xóa dữ liệu)
    # =========================
    @app_commands.command(name="apply", description="11. Liên kết Form vào Embed")
    @app_commands.describe(embed_name="Tên embed muốn liên kết nút gửi đơn")
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
    async def apply(self, interaction: discord.Interaction, embed_name: str, label: str = "Gửi đơn đăng ký"):
        await interaction.response.defer(ephemeral=True)
        try:
            btn_data = {
                "type": "button",
                "style": "secondary",
                "label": f"\u2800{label}",
                "emoji": f"{Emojis.MATTRANG}",
                "custom_id": f"yiyi:forms:open:{embed_name}", 
                "system": "forms"
            }

            # Kiểm tra sự tồn tại của Embed trước khi gắn nút
            if not await load_embed(interaction.guild.id, embed_name):
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{embed_name}` để liên kết.")

            updated = await atomic_update_button(interaction.guild.id, embed_name, action="update_by_id", custom_id=f"yiyi:forms:open:{embed_name}", button_data=btn_data)
            
            if not updated:
                success = await atomic_update_button(interaction.guild.id, embed_name, action="add", button_data=btn_data)
                if not success:
                    embed_err = discord.Embed(
                        title=f"{Emojis.HOICHAM} hmm...? có lỗi gì đó ở đây",
                        description=f"embed đã full nút hoặc không thể gắn thêm nút form vào lúc này.",
                        color=0xf8bbd0
                    )
                    return await interaction.followup.send(embed=embed_err)

            # [BẢO TỒN LOGIC CỦA SẾP] Apply chỉ làm nhiệm vụ gắn nút, không đè config.

            embed_success = discord.Embed(
                title=f"{Emojis.MATTRANG} liên kết với embed `{embed_name}` thành công",
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_success)
        except Exception as e:
            print(f"[LỖI FORM APPLY] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi liên kết nút: `{e}`")

    # =========================
    # LỆNH 4: SETTING (Industrial Verification)
    # =========================
    @app_commands.command(name="setting", description="Xem danh sách các Form đang hoạt động và lộ trình setup")
    async def forms_setting(self, interaction: discord.Interaction):
        """
        [DEFENSE LAYER] 
        Quét thực tế toàn bộ kho Form để phát hiện liên kết ma.
        """
        await interaction.response.defer(ephemeral=True)
        try:
            # Lấy toàn bộ danh sách form của server
            all_forms = await get_all_forms(interaction.guild.id)
            
            if not all_forms:
                return await interaction.followup.send(f"{Emojis.HOICHAM} hiện tại chưa có form nào được setup.")

            embed_dashboard = discord.Embed(
                title=f"{Emojis.MATTRANG} bảng điều khiển biểu mẫu",
                description="dưới đây là trạng thái thực tế của các form trên server:",
                color=0xf8bbd0
            )

            for form in all_forms:
                emb_name = form.get("embed_name", "Không rõ")
                # [VERIFY CHÉO]
                embed_exists = await load_embed(interaction.guild.id, emb_name)
                
                status_icon = "✅" if embed_exists else "⚠️"
                status_text = "Đang hoạt động" if embed_exists else "**Đã bị xoá (Liên kết ma)**"
                
                fields_count = len(form.get("fields", {}))
                
                embed_dashboard.add_field(
                    name=f"{status_icon} Form: {form.get('title', 'Chưa đặt tiêu đề')}",
                    value=(
                        f"• Embed: `{emb_name}`\n"
                        f"• Kênh Log: <#{form.get('log_channel_id')}> \n"
                        f"• Số trường: `{fields_count}/5`\n"
                        f"• Trạng thái: {status_text}"
                    ),
                    inline=False
                )

            await interaction.followup.send(embed=embed_dashboard)
        except Exception as e:
            print(f"[LỖI FORM SETTING] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Không thể bốc dữ liệu Dashboard: `{e}`")

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "forms"), None)
        if existing: p_cmd.remove_command("forms")
        p_cmd.add_command(FormsGroup())
        print("[LOAD] Success: commands.forms.forms_group (Industrial Anti-Hang Fix)", flush=True)
