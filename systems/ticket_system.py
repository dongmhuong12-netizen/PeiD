import discord
import io
import datetime
import asyncio 
from core.cache_manager import get_raw

FILE_KEY = "ticket_configs"

async def handle_ticket_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id")
    guild = interaction.guild
    user = interaction.user

    # Lấy cấu hình từ database
    db = get_raw(FILE_KEY)
    config = db.get(str(guild.id))

    if not config:
        return await interaction.response.send_message("❌ Hệ thống chưa được cấu hình. Liên hệ Admin nhé sếp!", ephemeral=True)

    # =========================
    # LOGIC 1: MỞ TICKET (Đã cập nhật Đa-Role)
    # =========================
    if custom_id == "yiyi:ticket:open":
        await interaction.response.defer(ephemeral=True)
        
        category_id = config.get("category_id")
        category = guild.get_channel(int(category_id)) if category_id else None

        if not category:
            return await interaction.followup.send("❌ Không tìm thấy danh mục hỗ trợ. Sếp setup lại nhé!", ephemeral=True)

        # Kiểm tra nếu user đã có ticket chưa
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            return await interaction.followup.send(f"⚠️ Sếp đã có một ticket đang mở tại {existing_channel.mention} rồi nhé!", ephemeral=True)

        # --- BẮT ĐẦU CẬP NHẬT MẠCH QUYỀN HẠN (MULTI-STAFF) ---
        # 1. Khởi tạo quyền cơ bản (Khóa mọi người, mở cho User và Bot)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # 2. Vòng lặp cấp quyền cho toàn bộ danh sách Staff Roles đã lưu
        staff_ids = config.get("staff_role_ids", [])
        for r_id in staff_ids:
            role = guild.get_role(int(r_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        # --- KẾT THÚC CẬP NHẬT ---

        # Tạo kênh với danh sách overwrites mới
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket hỗ trợ của {user.name} (ID: {user.id})"
        )

        # Gửi lời chào và nút Đóng (Giữ nguyên)
        embed = discord.Embed(
            title="🎫 TICKET HỖ TRỢ",
            description=f"Chào {user.mention}, Staff sẽ hỗ trợ sếp sớm nhất có thể.\nNhấn nút dưới đây để đóng ticket nếu đã giải quyết xong.",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View(timeout=None)
        close_btn = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id="yiyi:ticket:close", emoji="🔒")
        view.add_item(close_btn)

        await channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Đã tạo kênh hỗ trợ cho sếp tại {channel.mention}", ephemeral=True)

    # =========================
    # LOGIC 2: ĐÓNG TICKET & XUẤT TRANSCRIPT (GIỮ NGUYÊN)
    # =========================
    elif custom_id == "yiyi:ticket:close":
        await interaction.response.defer()
        
        log_id = config.get("log_channel_id")
        log_channel = guild.get_channel(int(log_id)) if log_id else None
        
        transcript_content = f"--- TRANSCRIPT TICKET: {interaction.channel.name} ---\n"
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
            await log_channel.send(f"🔒 **Ticket Closed:** `{interaction.channel.name}` đã được đóng bởi {user.mention}.", file=file)

        await interaction.followup.send("🔒 Đang đóng và xóa kênh trong 5 giây...")
        await asyncio.sleep(5)
        await interaction.channel.delete()
