import discord
from core.cache_manager import get_raw

FILE_KEY = "forms_configs"

# --- LỚP MODAL ĐỘNG ---
class DynamicFormModal(discord.ui.Modal):
    def __init__(self, form_title, fields_config, log_channel):
        # Thiết lập tiêu đề cho cửa sổ Popup (Giới hạn 45 ký tự của Discord)
        popup_title = (form_title or "📝 ĐƠN ĐĂNG KÝ")[:45]
        super().__init__(title=popup_title)
        
        self.log_channel = log_channel
        self.form_title = form_title or "📝 ĐƠN ĐĂNG KÝ MỚI"
        self.inputs = {}

        # Sắp xếp fields theo thứ tự 1-5 và thêm vào Modal
        sorted_keys = sorted(fields_config.keys(), key=lambda x: int(x))
        for key in sorted_keys:
            f = fields_config[key]
            text_input = discord.ui.TextInput(
                label=f["label"],
                placeholder=f["placeholder"],
                required=f["required"],
                # Nếu nhãn dài, tự động chuyển sang dạng Paragraph cho dễ nhập liệu
                style=discord.TextStyle.paragraph if len(f["label"]) > 15 else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.inputs[f["label"]] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        # [CẬP NHẬT] Sử dụng Form Title sếp đã set và xoá ID User cho thẩm mỹ
        embed = discord.Embed(
            title=self.form_title,
            description=f"Người gửi: {interaction.user.mention}", # Chỉ giữ lại mention
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        for label, text_input in self.inputs.items():
            embed.add_field(name=label, value=text_input.value or "N/A", inline=False)

        if self.log_channel:
            await self.log_channel.send(embed=embed)
            await interaction.response.send_message("✅ Đơn của sếp đã được gửi thành công!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Lỗi: Không tìm thấy kênh Log đơn.", ephemeral=True)

# --- TRẠM TRUNG CHUYỂN INTERACTION ---
async def handle_forms_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("yiyi:forms:open:"): return

    embed_name = custom_id.replace("yiyi:forms:open:", "")
    db = get_raw(FILE_KEY)
    config = db.get(str(interaction.guild.id), {}).get(embed_name)

    if not config or not config["fields"]:
        return await interaction.response.send_message("⚠️ Đơn này chưa được cấu hình nội dung sếp ơi!", ephemeral=True)

    try:
        log_channel = interaction.guild.get_channel(int(config["log_channel_id"]))
    except (ValueError, TypeError):
        log_channel = None
    
    # [CẬP NHẬT] Lấy Title sếp đã lưu từ Config để truyền vào Modal
    form_title = config.get("form_title")
    
    # Bật Modal cho User
    modal = DynamicFormModal(form_title=form_title, fields_config=config["fields"], log_channel=log_channel)
    await interaction.response.send_modal(modal)
