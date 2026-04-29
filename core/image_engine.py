import discord
import io
# [VÁ LỖI] Nạp emoji hệ thống để tránh NameError nhảy vào block except
from utils.emojis import Emojis

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Trạng thái: Đã kiểm duyệt (Vĩnh viễn - Không x2 ảnh - Đúng thứ tự DNA của Nguyệt).
    """

    # [NÂNG CẤP PHÒNG THỦ] Check quyền chủ động (Industrial Pro)
    perms = interaction.channel.permissions_for(interaction.guild.me)
    if not perms.attach_files:
        return await interaction.followup.send(
            f"{Emojis.HOICHAM} **yiyi** không có quyền `đính kèm file` tại kênh này. hãy kiểm tra lại nhé", 
            ephemeral=True
        )
    
    # 1. Kiểm tra định dạng (Ảnh, GIF, Video)
    valid_types = [
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/webp', 'video/mp4', 'video/quicktime', 'video/webm'
    ]
    
    if not file.content_type or not any(t in file.content_type for t in valid_types):
        return await interaction.followup.send(
            f"{Emojis.HOICHAM} **Invalid Format:** Vui lòng gửi Ảnh (PNG/JPG/WEBP), GIF hoặc Video (MP4/MOV).", 
            ephemeral=True
        )

    # 2. Giới hạn dung lượng (25MB)
    MAX_SIZE = 25 * 1024 * 1024 
    if file.size > MAX_SIZE:
        return await interaction.followup.send(
            f"{Emojis.HOICHAM} **File Too Large:** Dung lượng file vượt quá giới hạn cho phép (**25MB**).", 
            ephemeral=True
        )

    try:
        # 3. Đọc dữ liệu vào Buffer (Đảm bảo upload ổn định nhất)
        file_bytes = await file.read()
        file_buffer = io.BytesIO(file_bytes)
        discord_file = discord.File(file_buffer, filename=file.filename)

        # 4. Gửi file đính kèm để Discord tạo link vĩnh viễn
        msg = await interaction.followup.send(
            content=f"{Emojis.MATTRANG} **yiyi** đang xử lý...", 
            file=discord_file, 
            wait=True
        )

        # 5. Trích xuất link vĩnh viễn
        if not msg.attachments:
            raise Exception("Discord không phản hồi file đính kèm.")
            
        cdn_url = msg.attachments[0].url

        # 6. GIỮ NGUYÊN THỨ TỰ DNA CỦA NGUYỆT: Text -> Link xanh -> Code block
        # Cặp dấu < > đảm bảo link hiện full nhưng không đẻ thêm view ảnh thứ 2
        response_text = (
            f"{Emojis.MATTRANG}  tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"<{cdn_url}>\n"
            f"```{cdn_url}```"
        )
        
        # 7. Edit lại tin nhắn để hoàn tất khối duy nhất
        await msg.edit(content=response_text)

    except Exception as e:
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            await interaction.followup.send(
                f"{Emojis.HOICHAM} **Lỗi hệ thống:** **yiyi** không thể xử lý file. Hãy kiểm tra lại quyền của **yiyi** nhé.", 
                ephemeral=True
            )
        except:
            pass
