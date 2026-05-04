import discord
from core.cache_manager import get_raw
from utils.emojis import Emojis

FILE_KEY = "forms_configs"

# --- LỚP MODAL ĐỘNG ---
class DynamicFormModal(discord.ui.Modal):
    def __init__(self, form_title, fields_config, log_channel, show_thumbnail):
        # 1. Tiêu đề cửa sổ Popup sếp duyệt
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
                style=discord.TextStyle.paragraph if len(f["label"]) > 15 else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.inputs[f["label"]] = text_input

    async def on_submit(self, interaction: discord.Interaction):
        # 6. Embed Log với tiêu đề tùy chỉnh và Mention sạch (Đã xóa ID User)
        embed = discord.Embed(
            title=self.form_title,
            description=f"**Người gửi:** \n {interaction.user.mention}",
            color=0xf8bbd0,
            timestamp=discord.utils.utcnow()
        )
        
        # [MẠCH THUMBNAIL MỚI] Hiện avatar user nếu show_thumbnail = True
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

    embed_name = custom_id.replace("yiyi:forms:open:", "")
    db = get_raw(FILE_KEY)
    config = db.get(str(interaction.guild.id), {}).get(embed_name)

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
    except:
        log_channel = None
    
    form_title = config.get("form_title")
    # Lấy thêm trạng thái Thumbnail từ config
    show_thumbnail = config.get("show_thumbnail", True)
    
    # Truyền show_thumbnail vào Modal
    modal = DynamicFormModal(
        form_title=form_title, 
        fields_config=config["fields"], 
        log_channel=log_channel,
        show_thumbnail=show_thumbnail
    )
    await interaction.response.send_modal(modal)
