import discord
import io

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Fix dứt điểm: 'Internal Error', 'Lặp 2 ảnh' và 'Link 1 dòng'.
    """
    
    # 1. Kiểm tra định dạng (Ảnh, GIF, Video)
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
        # 3. Đọc dữ liệu vào Buffer để upload ổn định
        file_bytes = await file.read()
        file_buffer = io.BytesIO(file_bytes)
        discord_file = discord.File(file_buffer, filename=file.filename)

        # 4. Gửi file đính kèm (Bắt buộc để lấy link vĩnh viễn)
        # Sử dụng wait=True để nhận lại object tin nhắn
        msg = await interaction.followup.send(
            content="⌛ Đang xử lý...", 
            file=discord_file, 
            wait=True
        )

        # 5. Trích xuất link vĩnh viễn (https://cdn.discordapp.com/attachments/...)
        if not msg.attachments:
            raise Exception("Discord không nhả link attachment.")
            
        cdn_url = msg.attachments[0].url

        # 6. Ráp đúng thứ tự DNA của Nguyệt: Text -> Link xanh -> Link trong Code block
        # Thủ thuật <link> giúp hiện link full nhưng KHÔNG tạo thêm view ảnh thứ 2
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"<{cdn_url}>\n"
            f"```{cdn_url}```"
        )
        
        # 7. Edit lại tin nhắn để hoàn tất (Gộp 1 khối duy nhất)
        await msg.edit(content=response_text)

    except Exception as e:
        # Log lỗi ra Console để cậu theo dõi (flush=True để hiện ngay)
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            await interaction.followup.send(
                "❌ **Lỗi hệ thống:** Bot không thể xử lý file. Hãy kiểm tra quyền 'Đính kèm file' của Bot.", 
                ephemeral=True
            )
        except:
            pass


