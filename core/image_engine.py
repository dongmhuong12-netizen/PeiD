import discord

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Trực tiếp xuất link công khai ra kênh, gọn gàng, không log rác.
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
        # 3. Kết nối kênh hiện tại và kiểm tra quyền hạn thực tế
        channel = interaction.channel
        if not channel:
            return await interaction.followup.send("❌ **Channel Error:** Không thể xác định kênh hiện tại.", ephemeral=True)
        
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.attach_files:
            return await interaction.followup.send("❌ **Permission Error:** Bot thiếu quyền 'Gửi Tin Nhắn' hoặc 'Đính Kèm File' tại kênh này.", ephemeral=True)

        # 4. Trung chuyển file (Gửi thẳng ra kênh công khai để Discord tạo CDN vĩnh viễn)
        discord_file = await file.to_file()
        
        # Ép gửi public bất chấp thiết lập ephemeral của lệnh gốc
        public_msg = await channel.send(file=discord_file)

        # 5. Trích xuất link CDN trực tiếp từ tin nhắn vừa gửi
        cdn_url = public_msg.attachments[0].url

        # 6. Format y hệt Mimu: Dòng 1 (Link xanh clickable) - Dòng 2 (Code block để copy nhanh)
        mimu_format_text = f"{cdn_url}\n```{cdn_url}```"
        
        # Chỉnh sửa lại chính tin nhắn đó để chèn text vào
        await public_msg.edit(content=mimu_format_text)

        # 7. Tắt trạng thái "Bot đang suy nghĩ" bằng một thông báo ẩn cực nhỏ gọn
        await interaction.followup.send("✅ Đã tạo link thành công!", ephemeral=True)

    except Exception as e:
        # Giữ log ở Terminal để quản trị viên tra soát, tuyệt đối không rác ra kênh
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        await interaction.followup.send("❌ **Internal Error:** Đã xảy ra lỗi trong quá trình xử lý ảnh.", ephemeral=True)



