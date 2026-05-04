import discord
import io
import datetime
import asyncio 
from core.cache_manager import get_raw
from utils.emojis import Emojis # Đảm bảo đã nạp bộ emoji hệ thống

FILE_KEY = "ticket_configs"

async def handle_ticket_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id")
    guild = interaction.guild
    user = interaction.user

    # Lấy cấu hình từ database
    db = get_raw(FILE_KEY)
    config = db.get(str(guild.id))

    # [MỤC 1] Phản hồi khi chưa có cấu hình
    if not config:
        embed_no_config = discord.Embed(
            title=f"{Emojis.HOICHAM} hệ thống chưa có cấu hình.",
            description="cậu hãy liên hệ với các Admin để nhận sự hỗ trợ từ họ nhé.",
            color=0xf8bbd0
        )
        return await interaction.response.send_message(embed=embed_no_config, ephemeral=True)

    # =========================
    # LOGIC 1: MỞ TICKET
    # =========================
    if custom_id == "yiyi:ticket:open":
        await interaction.response.defer(ephemeral=True)
        
        category_id = config.get("category_id")
        category = guild.get_channel(int(category_id)) if category_id else None

        # [MỤC 2] Lỗi không tìm thấy danh mục/lỗi hệ thống
        if not category:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree...?",
                description=(
                    "có vẻ có lỗi gì đó đối với Ticket của cậu được tạo và gửi tới. "
                    "hãy thử lại sau một thời gian hoặc liên hệ với staff/thành viên hỗ trợ để nhận sự trợ giúp từ họ nhé."
                ),
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_err, ephemeral=True)

        # [MỤC 3] Kiểm tra ticket trùng (Đóng khung code kênh)
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            embed_exist = discord.Embed(
                description=f"{Emojis.MATTRANG} cậu đã có sẵn một Ticket đang mở sẵn từ chính cậu ở kênh {existing_channel.mention} rồi nhee, không được tạo thêm đâu.",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_exist, ephemeral=True)

        # --- GIỮ NGUYÊN LOGIC PHÂN QUYỀN (MULTI-STAFF) ---
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        staff_ids = config.get("staff_role_ids", [])
        for r_id in staff_ids:
            role = guild.get_role(int(r_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        # [MỤC 4] Tạo kênh (Giữ nguyên định dạng tên)
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket hỗ trợ của {user.name} (ID: {user.id})"
        )

        # [MỤC 5] Embed Lời Chào (Stylized theo ý sếp)
        welcome_embed = discord.Embed(
            title=f"{Emojis.MATTRANG} TICKET HỖ TRỢ",
            description=(
                f"• **chào cậu nhé, {user.mention}.**\n\n"
                "• kênh này được tạo ra để hỗ trợ giải đáp các thắc mắc của cậu. cậu có thể tự do đặt câu hỏi hoặc yêu trợ giúp.\n"
                "• **hãy yên tâm về quyền riêng tư:** chỉ có cậu và các staff được phân vai trò hỗ trợ mới có thể thấy kênh này.\n"
                f"• nhấn nút bên dưới để đóng Ticket nếu cậu không còn câu hỏi hay yêu cầu nào khác nhé {Emojis.YIYITIM}"
            ),
            color=0xf8bbd0
        )
        
        view = discord.ui.View(timeout=None)
        # [MỤC 7] Nút đóng Ticket (Giữ nguyên)
        close_btn = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id="yiyi:ticket:close", emoji="🔒")
        view.add_item(close_btn)

        await channel.send(embed=welcome_embed, view=view)
        
        # [MỤC 8] Phản hồi tạo thành công
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} tạo Ticket thành công. hãy tới kênh {channel.mention} để sử dụng nhé.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_success, ephemeral=True)

    # =========================
    # LOGIC 2: ĐÓNG TICKET & XUẤT TRANSCRIPT
    # =========================
    elif custom_id == "yiyi:ticket:close":
        await interaction.response.defer()
        
        log_id = config.get("log_channel_id")
        log_channel = guild.get_channel(int(log_id)) if log_id else None
        
        # [MỤC 9] Transcript Header mới
        transcript_content = f"--- NỘI DUNG TICKET: {interaction.channel.name} ---\n"
        transcript_content += f"Người mở: {interaction.channel.name.replace('ticket-', '')}\n"
        transcript_content += f"Thời gian đóng: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript_content += "------------------------------------------\n\n"

        async for message in interaction.channel.history(limit=None, oldest_first=True):
            time = message.created_at.strftime("%Y-%m-%d %H:%M")
            content = message.content if message.content else "[Tin nhắn không có nội dung văn bản]"
            transcript_content += f"[{time}] {message.author}: {content}\n"

        file_data = io.BytesIO(transcript_content.encode('utf-8'))
        file = discord.File(file_data, filename=f"transcript-{interaction.channel.name}.txt")

        if log_channel:
            # [MỤC 10] Embed Log khi đóng Ticket (Đóng khung tên kênh)
            log_embed = discord.Embed(
                description=f"{Emojis.MATTRANG} **Ticket Closed:** `{interaction.channel.name}` đã được đóng bởi {user.mention}. nội dung Ticket đã được lưu.",
                color=0xf8bbd0
            )
            await log_channel.send(embed=log_embed, file=file)

        # [MỤC 11] Thông báo đếm ngược (Giữ nguyên)
        await interaction.followup.send("🔒 Đang đóng và xóa kênh trong 5 giây...")
        await asyncio.sleep(5)
        await interaction.channel.delete()
