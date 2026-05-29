import discord
import re
from utils.emojis import Emojis

# [TÁCH BẠCH KIẾN TRÚC] Import thẳng hàm lấy dữ liệu từ kho Storage
from core.forms_storage import get_form_config

# ==========================================
# INTERACTION LOGIC (GIA CỐ BỘ LỌC EMOJI)
# ==========================================

class YiyiFormModal(discord.ui.Modal):
    """Lớp giao diện bảng nhập liệu hiện lên khi người dùng bấm nút."""
    def __init__(self, title, fields_data, log_channel_id, show_thumbnail):
        # 1. BẢO TỒN NGUYÊN BẢN (Để dành render đầy đủ emoji ra kênh Log)
        self.original_title = title.strip() if title else ""
        
        # 2. GỌT SẠCH CHO MENU MODAL (Chống lỗi Crash Discord do lố 45 ký tự)
        clean_title = re.sub(r'<a?:\w+:\d+>', '', self.original_title)
        clean_title = re.sub(r'\{[A-Za-z0-9_]+\}', '', clean_title).strip()
        safe_title = clean_title[:45] if clean_title else "Đơn đăng ký"
        
        super().__init__(title=safe_title)
        
        self.log_channel_id = log_channel_id
        self.show_thumbnail = show_thumbnail
        self.inputs = {}
        self.original_labels = {}

        # Sắp xếp các ô nhập liệu theo đúng thứ tự slot (1 -> 5)
        sorted_slots = sorted(fields_data.keys(), key=lambda x: int(x))

        for slot in sorted_slots:
            data = fields_data[slot]
            raw_label = data['label']
            raw_placeholder = data.get('placeholder') or "Nhập nội dung..."
            
            # Lưu lại nhãn nguyên bản phục vụ xuất Embed Log
            self.original_labels[slot] = raw_label
            
            # Cạo sạch Emoji và gọt chuẩn 45 ký tự cho Tên ô (Label) trên Menu Modal
            clean_label = re.sub(r'<a?:\w+:\d+>', '', raw_label)
            clean_label = re.sub(r'\{[A-Za-z0-9_]+\}', '', clean_label).strip()
            safe_label = clean_label[:45] if clean_label else "Nhập thông tin"
            
            # Cạo sạch Emoji và gọt chuẩn 100 ký tự cho Chú thích (Placeholder) trên Menu Modal
            clean_ph = re.sub(r'<a?:\w+:\d+>', '', raw_placeholder)
            clean_ph = re.sub(r'\{[A-Za-z0-9_]+\}', '', clean_ph).strip()
            safe_ph = clean_ph[:100] if clean_ph else "..."
            
            text_input = discord.ui.TextInput(
                label=safe_label,
                placeholder=safe_ph,
                required=data['required'],
                style=discord.TextStyle.paragraph if len(safe_label) > 15 else discord.TextStyle.short
            )
            self.add_item(text_input)
            self.inputs[slot] = text_input

    def _parse_emojis(self, text: str) -> str:
        """Cỗ máy dịch mã và biến số sang dạng emoji hiển thị thực tế của peiD"""
        if not text: return ""
        result = text
        for var_name, var_value in Emojis.__dict__.items():
            if not var_name.startswith("__") and isinstance(var_value, str):
                result = result.replace(f"{{{var_name}}}", var_value)
        return result

    async def on_submit(self, interaction: discord.Interaction):
        # Mạch gửi đơn về kênh log khi user nhấn Submit
        channel = interaction.guild.get_channel(int(self.log_channel_id))
        if not channel:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} **yiyi** không tìm thấy kênh gửi log, xin hãy kiểm tra lại cấu hình setup.", ephemeral=True)

        # 3. PHÂN LUỒNG QUYẾT ĐỊNH TIÊU ĐỀ EMBED TRẢ VỀ LOG
        if not self.original_title:
            # Nếu sếp KHÔNG cấu hình tiêu đề -> Trả về mặc định
            display_title = f"{Emojis.BUOMA} đơn đăng ký mới"
        else:
            # Nếu sếp ĐÃ cấu hình tiêu đề -> Dùng 100% chữ sếp thiết lập & dịch biến (bỏ hoàn toàn chữ mặc định)
            display_title = self._parse_emojis(self.original_title)

        embed_log = discord.Embed(
            title=display_title,
            color=0xe6e2dd,
            timestamp=discord.utils.utcnow()
        )
        
        # [KHOẢNG CÁCH INDUSTRIAL] Ép tạo dòng trống bằng \n\u200b
        # Kỹ thuật này giúp "Người gửi" tách biệt hoàn toàn với các trường bên dưới
        embed_log.add_field(
            name="Người gửi:", 
            value=f"{interaction.user.mention}\n\u200b", 
            inline=False
        )
        
        # Thêm các trường dữ liệu thực tế và dịch biến
        for slot in sorted(self.inputs.keys(), key=lambda x: int(x)):
            text_input = self.inputs[slot]
            
            # Khôi phục nhãn gốc mang đi dịch biến emoji, đồng thời dịch biến nội dung nhập của user
            display_label = self._parse_emojis(self.original_labels[slot])
            display_value = self._parse_emojis(text_input.value)
            
            embed_log.add_field(name=display_label, value=display_value, inline=False)
        
        # Hiện Avatar làm thumbnail ở góc trên bên phải theo chuẩn kiến trúc đồ họa
        if self.show_thumbnail:
            embed_log.set_thumbnail(url=interaction.user.display_avatar.url)

        await channel.send(embed=embed_log)
        await interaction.response.send_message(f"{Emojis.BUOMA} đơn đã được gửi đi thành công.", ephemeral=True)

async def handle_forms_interaction(interaction: discord.Interaction):
    """
    [ENTRY POINT] 
    Hàm điều phối tiếp nhận tương tác từ button_listener.py để hiển thị Modal Form.
    """
    custom_id = interaction.data.get("custom_id", "")
    parts = custom_id.split(":")
    if len(parts) < 4: return

    embed_name = parts[3]
    
    # Hút cấu hình Form siêu tốc từ core/forms_storage
    config = await get_form_config(interaction.guild.id, embed_name)

    if not config or not config.get("fields"):
        return await interaction.response.send_message(f"{Emojis.HOICHAM} form này chưa được thiết lập nội dung field.", ephemeral=True)

    # Hiện Modal truyền giá trị title rỗng nếu dữ liệu trống để kích hoạt mạch mặc định
    modal = YiyiFormModal(
        title=config.get("form_title", ""),
        fields_data=config.get("fields", {}),
        log_channel_id=config.get("log_channel_id"),
        show_thumbnail=config.get("show_thumbnail", True)
    )
    await interaction.response.send_modal(modal)
