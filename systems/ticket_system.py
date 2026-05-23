import discord
import io
import datetime
import asyncio 
from core.ticket_storage import get_ticket_config # [CẤY MỚI] Trí nhớ Cloud Atlas
from utils.emojis import Emojis

async def handle_ticket_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id")
    guild = interaction.guild
    user = interaction.user

    # [KẾT NỐI MẠCH] Truy vấn cấu hình Ticket từ Cloud Atlas
    config = await get_ticket_config(guild.id) 

    # [DEF - VÁ LỖI ĐỒNG BỘ] 
    # Vì get_ticket_config giờ trả về {} nên phải check thêm key category_id
    if not config or not config.get("category_id"):
        embed_no_config = discord.Embed(
            title=f"{Emojis.HOICHAM} hệ thống chưa có cấu hình.",
            description="cậu hãy liên hệ với các Admin để nhận sự hỗ trợ từ họ nhé.",
            color=0xe6e2dd
        )
        # Nếu là nút bấm mở ticket thì send_message, còn lại tùy biến theo mạch logic
        if not interaction.response.is_done():
            return await interaction.response.send_message(embed=embed_no_config, ephemeral=True)
        else:
            return await interaction.followup.send(embed=embed_no_config, ephemeral=True)

    # =========================
    # LOGIC 1: MỞ TICKET
    # =========================
    if custom_id == "yiyi:ticket:open":
        # QUY TẮC 3S: Defer ngay lập tức để giữ mạch kết nối (Industrial Standard)
        await interaction.response.defer(ephemeral=True)
        
        category_id = config.get("category_id")
        # IT Pro: Đảm bảo lấy channel chính xác từ Cache hoặc API
        category = guild.get_channel(int(category_id)) if category_id else None
        if not category and category_id:
            try: category = await guild.fetch_channel(int(category_id))
            except: category = None

        # [MỤC 2] Lỗi không tìm thấy danh mục/lỗi hệ thống
        if not category:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree...?",
                description=(
                    "có vẻ danh mục chứa Ticket đã bị xóa hoặc không hợp lệ. "
                    "hãy liên hệ với staff/thành viên hỗ trợ để thiết lập lại bằng `/p ticket setup` nhé."
                ),
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err, ephemeral=True)

        # [MỤC 3] Kiểm tra ticket trùng (Đã chuẩn hóa lower toàn diện)
        ticket_name = f"ticket-{user.name.lower()}"
        existing_channel = discord.utils.get(guild.channels, name=ticket_name)
        if existing_channel:
            embed_exist = discord.Embed(
                description=f"{Emojis.BUOMA} cậu đã có một Ticket đang mở sẵn từ chính cậu ở kênh {existing_channel.mention} rồi nhee, không được tạo thêm đâu.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_exist, ephemeral=True)

        # --- GIỮ NGUYÊN LOGIC PHÂN QUYỀN (MULTI-STAFF) ---
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # Nạp danh sách Staff từ cấu hình Cloud
        staff_ids = config.get("staff_roles", [])
        for r_id in staff_ids:
            try:
                role = guild.get_role(int(r_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            except: continue

        # [MỤC 4] Tạo kênh (Đã đồng bộ hóa định dạng tên)
        channel = await guild.create_text_channel(
            name=ticket_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket hỗ trợ của {user.name} (ID: {user.id})"
        )

        # [MỤC 5] Embed Lời Chào (Stylized theo DNA của sếp)
        welcome_embed = discord.Embed(
            title=f"{Emojis.BUOMA} TICKET HỖ TRỢ",
            description=(
                f"• **chào cậu nhé, {user.mention}.**\n\n"
                "• kênh này được tạo ra để hỗ trợ giải đáp các thắc mắc của cậu. cậu có thể tự do đặt câu hỏi hoặc yêu cầu trợ giúp.\n"
                "• **hãy yên tâm về quyền riêng tư:** chỉ có cậu và các staff được phân vai trò hỗ trợ mới có thể thấy kênh này.\n"
                f"• nhấn nút bên dưới để đóng Ticket nếu cậu không còn câu hỏi hay yêu cầu nào khác nhé {Emojis.YIYITIM}"
            ),
            color=0xe6e2dd
        )
        
        view = discord.ui.View(timeout=None)
        # [MỤC 7] Nút đóng Ticket
        close_btn = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id="yiyi:ticket:close", emoji=Emojis.BUOMB)
        view.add_item(close_btn)

        await channel.send(embed=welcome_embed, view=view)
        
        # [MỤC 8] Phản hồi tạo thành công
        embed_success = discord.Embed(
            description=f"{Emojis.BUOMA} tạo Ticket thành công. hãy tới kênh {channel.mention} để sử dụng nhé.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success, ephemeral=True)

    # =========================
    # LOGIC 2: ĐÓNG TICKET & XUẤT TRANSCRIPT
    # =========================
    elif custom_id == "yiyi:ticket:close":
        await interaction.response.defer()
        
        log_id = config.get("log_channel_id")
        log_channel = guild.get_channel(int(log_id)) if log_id else None
        if not log_channel and log_id:
            try: log_channel = await guild.fetch_channel(int(log_id))
            except: log_channel = None
        
        # [MỤC 9] Transcript Header
        transcript_content = f"--- NỘI DUNG TICKET: {interaction.channel.name} ---\n"
        transcript_content += f"Người mở: {interaction.channel.name.replace('ticket-', '')}\n"
        transcript_content += f"Thời gian đóng: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript_content += "------------------------------------------\n\n"

        # Thu thập toàn bộ lịch sử tin nhắn (Industrial Standard for Transcripts)
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            time = message.created_at.strftime("%Y-%m-%d %H:%M")
            content = message.content if message.content else "[Tin nhắn không có nội dung văn bản]"
            transcript_content += f"[{time}] {message.author}: {content}\n"

        file_data = io.BytesIO(transcript_content.encode('utf-8'))
        file = discord.File(file_data, filename=f"transcript-{interaction.channel.name}.txt")

        if log_channel:
            # [MỤC 10] Embed Log khi đóng Ticket
            log_embed = discord.Embed(
                description=f"{Emojis.BUOMA} **Ticket Closed:** `{interaction.channel.name}` đã được đóng bởi {user.mention}. nội dung Ticket đã được lưu.",
                color=0xe6e2dd
            )
            await log_channel.send(embed=log_embed, file=file)

        # [MỤC 11] Thông báo đếm ngược và Xóa kênh
        await interaction.followup.send(f"{Emojis.BUOMB} Đang đóng và xóa kênh trong 5 giây...")
        await asyncio.sleep(5)
        await interaction.channel.delete()
