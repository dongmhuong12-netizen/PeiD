import discord

async def process_image_upload(interaction: discord.Interaction, file: discord.Attachment, bot: discord.Client):
    """
    Hệ thống Logic lõi: Upload và tạo link CDN chuẩn Mimu Style.
    Tối ưu siêu nhẹ: Trích xuất trực tiếp URL từ slash command, không re-upload (chống x2 ảnh).
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
        # 3. IT Pro: Lấy trực tiếp URL mà Discord đã tạo khi user chạy lệnh.
        # KHÔNG tải file về và KHÔNG gửi lại -> Loại bỏ hoàn toàn lỗi hiển thị x2 ảnh.
        cdn_url = file.url

        # 4. Format chuẩn 100% theo đúng thứ tự Nguyệt yêu cầu:
        # - Đoạn text hướng dẫn (trên cùng)
        # - Link xanh công khai (ở giữa)
        # - Code block chứa link (dưới cùng)
        response_text = (
            "tạo link thành công, có thể sao chép link bên dưới để sử dụng\n"
            "lưu ý: **không được** xoá link hoặc kênh này, nếu không link sẽ không hợp lệ.\n\n"
            f"{cdn_url}\n"
            f"```{cdn_url}```"
        )
        
        # 5. Gửi 1 khối tin nhắn duy nhất
        await interaction.followup.send(content=response_text)

    except Exception as e:
        # Giữ log rác ở Terminal, không hiện ra Discord
        print(f"[IMAGE ENGINE ERROR] {e}", flush=True)
        try:
            await interaction.followup.send("❌ **Internal Error:** Đã xảy ra lỗi trong quá trình xử lý ảnh.", ephemeral=True)
        except:
            pass
