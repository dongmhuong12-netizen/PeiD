import discord
import io
import datetime
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
    # LOGIC 1: MỞ TICKET
    # =========================
    if custom_id == "yiyi:ticket:open":
        await interaction.response.defer(ephemeral=True)
        
        category = guild.get_channel(int(config["category_id"]))
        staff_role = guild.get_role(int(config["staff_role_id"]))

        # Kiểm tra nếu user đã có ticket chưa (Chống spam)
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            return await interaction.followup.send(f"⚠️ Sếp đã có một ticket đang mở tại {existing_channel.mention} rồi nhé!", ephemeral=True)

        # Thiết lập quyền hạn (Permissions) - Cực kỳ quan trọng
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), # Khóa với tất cả
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), # Mở cho User
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), # Mở cho Staff
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) # Mở cho Bot
        }

        # Tạo kênh
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket hỗ trợ của {user.name} (ID: {user.id})"
        )

        # Gửi lời chào và nút Đóng
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
    # LOGIC 2: ĐÓNG TICKET & XUẤT TRANSCRIPT
    # =========================
    elif custom_id == "yiyi:ticket:close":
        await interaction.response.defer()
        
        log_channel = guild.get_channel(int(config["log_channel_id"]))
        
        # Tạo Transcript đơn giản (Text-based)
        transcript_content = f"--- TRANSCRIPT TICKET: {interaction.channel.name} ---\n"
        transcript_content += f"Người mở: {interaction.channel.name.replace('ticket-', '')}\n"
        transcript_content += f"Thời gian đóng: {datetime.datetime.now()}\n"
        transcript_content += "------------------------------------------\n\n"

        async for message in interaction.channel.history(limit=None, oldest_first=True):
            time = message.created_at.strftime("%Y-%m-%d %H:%M")
            transcript_content += f"[{time}] {message.author}: {message.content}\n"

        # Đóng gói file
        file = discord.File(io.BytesIO(transcript_content.encode()), filename=f"transcript-{interaction.channel.name}.txt")

        # Gửi log
        if log_channel:
            await log_channel.send(f"🔒 **Ticket Closed:** `{interaction.channel.name}` đã được đóng bởi {user.mention}.", file=file)

        await interaction.followup.send("🔒 Đang đóng và xóa kênh trong 5 giây...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

