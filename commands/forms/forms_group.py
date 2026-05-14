import discord
from discord import app_commands
from discord.ext import commands
import re
import traceback

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
    # LỆNH 1: SETUP NỀN (Fix Treo & Chuẩn hóa logic Thumbnail)
    # =========================
    @app_commands.command(name="setup", description="1. Setup đơn, tiêu đề và kênh nhận kết quả")
    @app_commands.describe(
        embed_name="2. Tên embed gắn form",
        form_title="4. Tiêu đề hiển thị trên đơn",
        log_channel_id="3. ID hoặc tag kênh nhận kết quả",
        show_thumbnail="Lựa chọn hiển thị Avatar người gửi vào Đơn (kênh log)"
    )
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
    @app_commands.choices(slot=[
        app_commands.Choice(name="Trường 1", value=1),
        app_commands.Choice(name="Trường 2", value=2),
        app_commands.Choice(name="Trường 3", value=3),
        app_commands.Choice(name="Trường 4", value=4),
        app_commands.Choice(name="Trường 5", value=5),
    ])
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
    async def apply(self, interaction: discord.Interaction, embed_name: str, label: str = "Gửi đơn đăng ký"):
        await interaction.response.defer(ephemeral=True)
        try:
            btn_data = {
                "type": "button",
                "style": "success",
                "label": label,
                "emoji": "📝",
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

            # [CHỐT HẠ] Đã xóa khối logic "update_form_base(title=None...)" gây "mất trí nhớ" cho Form.
            # Từ nay apply chỉ làm đúng chức năng gắn nút, không đụng chạm vào file config setup của sếp nữa.

            embed_success = discord.Embed(
                title=f"{Emojis.MATTRANG} liên kết với embed `{embed_name}` thành công",
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_success)
        except Exception as e:
            print(f"[LỖI FORM APPLY] {e}")
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi liên kết nút: `{e}`")

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "forms"), None)
        if existing: p_cmd.remove_command("forms")
        p_cmd.add_command(FormsGroup())
        print("[LOAD] Success: commands.forms.forms_group (Industrial Anti-Hang Fix)", flush=True)
