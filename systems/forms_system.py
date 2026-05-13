import discord
from utils.emojis import Emojis
from core.forms_storage import get_form_config # [CẤY MỚI] Trí nhớ Cloud

# --- LỚP MODAL ĐỘNG ---
class DynamicFormModal(discord.ui.Modal):
    def __init__(self, form_title, fields_config, log_channel, show_thumbnail):
        # 1. Tiêu đề cửa sổ Popup sếp duyệt (Giới hạn 45 ký tự)
        popup_title = f"{Emojis.MATTRANG} ĐƠN ĐĂNG KÝ"
        super().__init__(title=popup_title[:45])
        
        self.log_channel = log_channel
        self.form_title = form_title or f"{Emojis.MATTRANG} ĐƠN ĐĂNG KÝ MỚI"
        self.show_thumbnail = show_thumbnail
        self.inputs = {}

        # Giữ nguyên logic sắp xếp fields 1-5
        sorted_keys = sorted(fields_config.keys(), key=lambda x: int(x))
        for key in sorted_keys:
            f = fields_config[key]
            text_input = discord.ui.TextInput(
                label=f["label"],
                placeholder=f["placeholder"],
                required=f["required"],
                # Tự động chuyển kiểu Paragraph nếu nhãn quá dài (IT Pro)
                style=discord.TextStyle.paragraph if len(f["label"]) > 15 else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.inputs[f["label"]] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        # 6. Embed Log với tiêu đề tùy chỉnh và Mention sạch
        embed = discord.Embed(
            title=self.form_title,
            description=f"**Người gửi:** \n {interaction.user.mention}",
            color=0xf8bbd0,
            timestamp=discord.utils.utcnow()
        )
        
        # [MẠCH THUMBNAIL] Hiện avatar user nếu show_thumbnail = True
        if self.show_thumbnail:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        for label, text_input in self.inputs.items():
            # 7. Nếu trống thì hiện 'none'
            val = text_input.value if text_input.value else "`none`"
            embed.add_field(name=label, value=val, inline=False)

        if self.log_channel:
            try:
                await self.log_channel.send(embed=embed)
                # 2. Phản hồi thành công sếp duyệt
                await interaction.response.send_message(
                    f"{Emojis.MATTRANG} đơn của cậu đã được gửi đi thành công.", 
                    ephemeral=True
                )
            except:
                # 3. Lỗi kênh log/quyền hạn
                await interaction.response.send_message(
                    f"{Emojis.HOICHAM} aree... có vẻ có lỗi gì đó đối với nơi mà đơn của cậu được gửi tới. hãy thử lại sau hoặc tìm các staff/thành viên hỗ trợ để được giúp đỡ nhé.", 
                    ephemeral=True
                )
        else:
            # 3. Không tìm thấy kênh log
            await interaction.response.send_message(
                f"{Emojis.HOICHAM} aree... có vẻ có lỗi gì đó đối với nơi mà đơn của cậu được gửi tới. hãy thử lại sau hoặc tìm các staff/thành viên hỗ trợ để được giúp đỡ nhé.", 
                ephemeral=True
            )

# --- TRẠM TRUNG CHUYỂN INTERACTION ---
async def handle_forms_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("yiyi:forms:open:"): return

    # Trích xuất tên embed từ custom_id
    embed_name = custom_id.replace("yiyi:forms:open:", "")
    
    # [KẾT NỐI MẠCH] Truy vấn cấu hình Form từ Cloud Atlas thay cho cache cũ
    config = await get_form_config(interaction.guild.id, embed_name)

    # 4. Khi chưa cấu hình field
    if not config or not config.get("fields"):
        return await interaction.response.send_message(
            f"{Emojis.MATTRANG} chưa thể tạo đơn. cậu hãy thử lại sau một thời gian nhé", 
            ephemeral=True
        )

    # Giữ nguyên logic lấy kênh log
    try:
        log_id = config.get("log_channel_id")
        log_channel = interaction.guild.get_channel(int(log_id)) if log_id else None
        if not log_channel:
            # IT Pro: Fetch nếu cache guild chưa nạp kênh
            log_channel = await interaction.guild.fetch_channel(int(log_id))
    except:
        log_channel = None
    
    form_title = config.get("form_title")
    # Lấy thêm trạng thái Thumbnail từ config (Mặc định là True)
    show_thumbnail = config.get("show_thumbnail", True)
    
    # Khởi tạo và hiển thị Modal
    modal = DynamicFormModal(
        form_title=form_title, 
        fields_config=config["fields"], 
        log_channel=log_channel,
        show_thumbnail=show_thumbnail
    )
    await interaction.response.send_modal(modal)
