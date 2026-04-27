import discord

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Fix dứt điểm lỗi link bị thu gọn thành icon ghim. Khôi phục link vĩnh viễn FULL dài.
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
        # 3. Chuyển đổi file sang chuẩn Discord File
        discord_file = await file.to_file()

        # 4. IT PRO TRICK: Gửi file lên kênh kèm text tạm thời
        # Hành động này ép Discord phải nhả ra cái link CDN "attachments/..." vĩnh viễn cực dài
        msg = await interaction.followup.send(content="⌛ Đang tạo link...", file=discord_file)

        # 5. Rút cái link vĩnh viễn cực dài đó ra
        cdn_url = msg.attachments[0].url

        # 6. Lắp ráp text theo đúng DNA Nguyệt yêu cầu: Text -> Link dài -> Code block
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"{cdn_url}\n"
            f"```{cdn_url}```"
        )
        
        # 7. Edit lại chính tin nhắn vừa gửi, đắp text xịn vào
        # Vì gói gọn trong 1 tin nhắn có đính kèm, Discord auto nhận diện và CHỈ hiển thị 1 ảnh dưới cùng!
        await msg.edit(content=response_text)

    except Exception as e:
        # Giữ log rác ở Terminal
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            await interaction.followup.send("❌ **Internal Error:** Đã xảy ra lỗi trong quá trình xử lý ảnh.", ephemeral=True)
        except:
            pass
