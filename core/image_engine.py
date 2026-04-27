import discord

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Link vĩnh viễn + Đầy đủ Link Xanh + Triệt tiêu x2 ảnh bằng suppress=True.
    """
    
    # 1. Kiểm tra định dạng (Hỗ trợ Ảnh, GIF và Video)
    valid_types = [
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/webp', 'video/mp4', 'video/quicktime', 'video/webm'
    ]
    
    if not file.content_type or not any(t in file.content_type for t in valid_types):
        return await interaction.followup.send(
            "❌ **Invalid Format:** Vui lòng gửi Ảnh (PNG/JPG/WEBP), GIF hoặc Video (MP4/MOV).", 
            ephemeral=True
        )

    # 2. Giới hạn dung lượng an toàn (25MB chuẩn Discord)
    MAX_SIZE = 25 * 1024 * 1024 
    if file.size > MAX_SIZE:
        return await interaction.followup.send(
            "❌ **File Too Large:** Dung lượng file vượt quá giới hạn cho phép (**25MB**).", 
            ephemeral=True
        )

    try:
        # 3. IT Pro: Chuyển file sang chuẩn discord.File
        discord_file = await file.to_file()

        # 4. GỬI FILE RA KÊNH (Bắt buộc để Discord cấp link CDN vĩnh viễn)
        msg = await interaction.followup.send(file=discord_file, wait=True)

        # 5. Trích xuất link vĩnh viễn từ tin nhắn vừa gửi
        cdn_url = msg.attachments[0].url

        # 6. KHÔI PHỤC ĐẦY ĐỦ DNA (Text -> Link xanh -> Code Block)
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"{cdn_url}\n"
            f"```{cdn_url}```"
        )
        
        # 7. Edit lại tin nhắn:
        # - suppress=True: Tắt khung xem trước của cái link xanh (Ngăn chặn triệt để x2 ảnh)
        # - Discord tự động hiển thị link xanh thành 1 dòng gọn gàng + 1 ảnh gốc ở dưới cùng.
        await msg.edit(content=response_text, suppress=True)

    except Exception as e:
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            await interaction.followup.send("❌ **Internal Error:** Đã xảy ra lỗi trong quá trình xử lý ảnh.", ephemeral=True)
        except:
            pass



