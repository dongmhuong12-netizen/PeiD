import discord
import datetime

# ID của kênh kho lưu trữ (Nguyệt thay ID thật của cậu vào đây nhé)
# Gợi ý: Tạo một kênh riêng tư, chỉ Bot có quyền xem và gửi tin nhắn để làm "kho".
STORAGE_CHANNEL_ID = 000000000000000000 

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Xử lý upload và tạo link CDN vĩnh viễn.
    Thiết kế theo chuẩn Pro cho bot lớn (Mimu-style).
    """
    
    # 1. Kiểm tra định dạng (Hỗ trợ Ảnh, GIF và Video chất lượng cao)
    valid_types = [
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/webp', 'video/mp4', 'video/quicktime', 'video/webm'
    ]
    
    # Kiểm tra loại file thông qua thuộc tính content_type của Discord
    if not file.content_type or not any(t in file.content_type for t in valid_types):
        return await interaction.followup.send(
            "❌ **Invalid Format:** Vui lòng gửi Ảnh (PNG/JPG/WEBP), GIF hoặc Video (MP4/MOV).", 
            ephemeral=True
        )

    # 2. Giới hạn dung lượng (25MB là con số chuẩn để Bot không bị treo khi xử lý file nặng)
    MAX_SIZE = 25 * 1024 * 1024 # 25MB
    if file.size > MAX_SIZE:
        return await interaction.followup.send(
            "❌ **File Too Large:** Dung lượng file vượt quá giới hạn cho phép (**25MB**).", 
            ephemeral=True
        )

    try:
        # 3. Kết nối kho chứa và kiểm tra quyền hạn thực tế của Bot
        storage_channel = bot.get_channel(STORAGE_CHANNEL_ID)
        if not storage_channel:
            return await interaction.followup.send("❌ **Storage Error:** Không tìm thấy Storage Channel. Hãy kiểm tra lại ID cấu hình.", ephemeral=True)
        
        perms = storage_channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.attach_files:
            return await interaction.followup.send("❌ **Permission Error:** Bot thiếu quyền đính kèm file trong kho lưu trữ.", ephemeral=True)

        # 4. Trung chuyển file và lưu Log Metadata để phục vụ tra soát sau này
        discord_file = await file.to_file()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ghi log rõ ràng trong kênh kho: Biết rõ ai gửi, gửi cái gì, dung lượng bao nhiêu
        log_content = (
            f"**─── New CDN Upload ───**\n"
            f"👤 **User:** {interaction.user} (`{interaction.user.id}`)\n"
            f"📅 **Date:** {timestamp}\n"
            f"📄 **File:** `{file.filename}` ({round(file.size/1024/1024, 2)} MB)"
        )
        
        storage_msg = await storage_channel.send(content=log_content, file=discord_file)

        # 5. Trích xuất link CDN trực tiếp (Link này sẽ vĩnh viễn nếu tin nhắn kho không bị xóa)
        cdn_url = storage_msg.attachments[0].url

        # 6. Trả kết quả theo đúng quy tắc Nguyệt yêu cầu: Hướng dẫn -> Link xanh -> Code block copy
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"{cdn_url}\n"
            f"```{cdn_url}```"
        )
        
        await interaction.followup.send(content=response_text)

    except Exception as e:
        # Xuất log lỗi chi tiết ra Terminal kèm flush để tránh mất dữ liệu log
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        await interaction.followup.send("❌ **Internal Error:** Đã xảy ra lỗi trong quá trình xử lý ảnh.", ephemeral=True)

