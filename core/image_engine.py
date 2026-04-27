import discord
import io

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Fix dứt điểm lỗi 'Internal Error' bằng cách sử dụng BytesIO buffer.
    Fix dứt điểm lỗi x2 ảnh bằng suppress=True.
    """
    
    # 1. Kiểm tra định dạng
    valid_types = [
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/webp', 'video/mp4', 'video/quicktime', 'video/webm'
    ]
    
    if not file.content_type or not any(t in file.content_type for t in valid_types):
        return await interaction.followup.send(
            "❌ **Invalid Format:** Vui lòng gửi Ảnh (PNG/JPG/WEBP), GIF hoặc Video (MP4/MOV).", 
            ephemeral=True
        )

    # 2. Giới hạn dung lượng (25MB)
    MAX_SIZE = 25 * 1024 * 1024 
    if file.size > MAX_SIZE:
        return await interaction.followup.send(
            "❌ **File Too Large:** Dung lượng file vượt quá giới hạn cho phép (**25MB**).", 
            ephemeral=True
        )

    try:
        # 3. Đọc dữ liệu file vào Buffer (Cách này cực kỳ ổn định, tránh Internal Error)
        file_bytes = await file.read()
        file_buffer = io.BytesIO(file_bytes)
        discord_file = discord.File(file_buffer, filename=file.filename)

        # 4. Gửi file đính kèm để lấy link vĩnh viễn
        # content tạm thời để Discord khởi tạo tin nhắn
        msg = await interaction.followup.send(
            content="⌛ Đang xử lý...", 
            file=discord_file, 
            wait=True
        )

        # 5. Trích xuất link vĩnh viễn
        cdn_url = msg.attachments[0].url

        # 6. Ráp đúng thứ tự DNA của Nguyệt: Text -> Link xanh -> Link trong Code block
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"{cdn_url}\n"
            f"```{cdn_url}```"
        )
        
        # 7. Edit để chèn text và SUPPRESS (Tắt link preview để không bị x2 ảnh)
        await msg.edit(content=response_text, suppress=True)

    except Exception as e:
        # In lỗi chi tiết ra console để cậu kiểm tra nếu vẫn gặp sự cố
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            # Thông báo lỗi cụ thể hơn cho user
            await interaction.followup.send(
                f"❌ **Lỗi hệ thống:** Không thể upload file (Có thể do Bot thiếu quyền hoặc file lỗi).", 
                ephemeral=True
            )
        except:
            pass


