import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import asyncio

from core.embed_storage import load_embed
from core.embed_sender import send_embed
# Kéo hàm Autocomplete và View từ file chính sang
from commands.embed.embed_group import create_embed_view, embed_name_autocomplete 
from utils.emojis import Emojis

# [NÂNG CẤP CHIẾN LƯỢC] Khóa chặt múi giờ Việt Nam (GMT+7) bất chấp cấu hình VPS
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))

class EmbedScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_col = getattr(bot.db, "db", bot.db)["scheduled_embeds"]
        
        # [MẠCH NHÓM LỆNH CẦU NỐI VÀO /P]
        self.embed_scheduler_group = app_commands.Group(name="scheduler", description="quản lý lịch gửi embed tự động")
        
        self.scheduler_loop.start()

    def cog_unload(self):
        self.scheduler_loop.cancel()

    # Vòng lặp "Trái tim" - Quét mỗi 60 giây
    @tasks.loop(seconds=60)
    async def scheduler_loop(self):
        # [KHIÊN 1] Bắt buộc chờ Bot boot xong 100% vào Discord mới bắt đầu quét
        await self.bot.wait_until_ready()
        
        # [KHIÊN 2] Dùng utcnow() chuẩn của Discord API để tránh bị nhiễu do OS của VPS
        now = discord.utils.utcnow().timestamp()
        
        # Tìm các task đã đến giờ
        cursor = self.db_col.find({"scheduled_at": {"$lte": now}})
        async for task in cursor:
            try:
                guild = self.bot.get_guild(int(task["guild_id"]))
                if not guild: continue
                
                channel = guild.get_channel(int(task["channel_id"]))
                if not channel: continue
                
                # Load dữ liệu (Sử dụng lại hàm load của sếp)
                data = await load_embed(guild.id, task["embed_name"])
                if not data: continue
                
                # Tạo view & Gửi (Sử dụng lại logic send_embed & create_embed_view của sếp)
                view = create_embed_view(data)
                user = await guild.fetch_member(task["user_id"]) if task.get("user_id") else None
                
                await send_embed(channel, data, guild, user, embed_name=task["embed_name"], view=view)
                
            except Exception as e:
                # Nếu quá trình gửi phát sinh lỗi, nó sẽ in ra màn hình VPS thay vì làm sập bot
                print(f"[Scheduler Error] Lỗi khi gửi embed {task.get('embed_name')}: {e}", flush=True)
            finally:
                # [CHỐT CHẶN TỐI THƯỢNG] 
                # Nhờ lệnh "finally", dù đoạn trên chạy thành công, hay dính lỗi (Exception), hay bị (continue)...
                # Hệ thống ĐỀU BẮT BUỘC thực thi lệnh XÓA TASK NÀY KHỎI DATABASE.
                # Khai tử vĩnh viễn hiện tượng Zombie Task (Gửi lặp lại đồ cũ).
                await self.db_col.delete_one({"_id": task["_id"]})

    @app_commands.command(name="schedule", description="lên lịch gửi embed vào thời gian chỉ định")
    @app_commands.describe(
        channel="kênh đích cần gửi",
        name="chọn embed muốn lên lịch từ danh sách",
        time_str="nhập thời gian theo giờ VN (Định dạng: DD/MM/YYYY HH:MM - VD: 20/10/2026 20:00)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete) # BẬT LẠI AUTOCOMPLETE
    async def schedule(self, interaction: discord.Interaction, channel: discord.TextChannel, name: str, time_str: str):
        await interaction.response.defer(ephemeral=True)
        
        # 1. Parse thời gian & Ép xung về múi giờ VN (GMT+7)
        try:
            dt = datetime.datetime.strptime(time_str, "%d/%m/%Y %H:%M")
            dt = dt.replace(tzinfo=VN_TZ) # Ép nó hiểu là giờ Việt Nam
            scheduled_at = dt.timestamp() # Chuyển về số giây chuẩn để so sánh
            
            # Check quá khứ: Lấy giờ hiện tại chuẩn để so sánh
            if scheduled_at < datetime.datetime.now().timestamp():
                return await interaction.followup.send(f"{Emojis.HOICHAM} thời gian này đã qua rồi, cậu hãy nhập thời gian tương lai nhé!", ephemeral=True)
        except ValueError:
            return await interaction.followup.send(f"{Emojis.HOICHAM} sai định dạng thời gian. Hãy nhập theo: `DD/MM/YYYY HH:MM` (VD: 20/10/2026 14:00)", ephemeral=True)

        # 2. Kiểm tra Embed tồn tại
        data = await load_embed(interaction.guild.id, name)
        if not data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{name}`.", ephemeral=True)

        # 3. Lưu vào DB với timestamp tuyệt đối
        await self.db_col.insert_one({
            "guild_id": str(interaction.guild.id),
            "channel_id": str(channel.id),
            "embed_name": name,
            "scheduled_at": scheduled_at,
            "user_id": interaction.user.id
        })

        await interaction.followup.send(
            f"{Emojis.BUOMA} đã lên lịch gửi embed `{name}` vào {time_str} tại kênh {channel.mention}.", 
            ephemeral=True
        )

    @app_commands.command(name="schedule_list", description="kiểm tra danh sách các embed đang chờ gửi")
    async def schedule_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Kéo toàn bộ task của server hiện tại, sắp xếp theo thời gian gửi gần nhất
        cursor = self.db_col.find({"guild_id": str(interaction.guild.id)}).sort("scheduled_at", 1)
        tasks_list = await cursor.to_list(length=20) # Hiển thị tối đa 20 task
        
        if not tasks_list:
            return await interaction.followup.send(f"{Emojis.BUOMA} hiện tại không có embed nào nằm trong hàng chờ nhe cậu.", ephemeral=True)
            
        desc = ""
        for i, task in enumerate(tasks_list, 1):
            channel_id = task.get("channel_id")
            emb_name = task.get("embed_name")
            timestamp = int(task.get("scheduled_at"))
            
            desc += f"**{i}.** Embed `{emb_name}` ➜ <#{channel_id}>\n"
            # Sử dụng chính biến đếm ngược ma thuật của Discord để báo cáo chính xác
            desc += f"└ ⏰ Khai hỏa: <t:{timestamp}:F> (<t:{timestamp}:R>)\n\n"
            
        embed_list = discord.Embed(
            title=f"🕒 danh sách embed hẹn giờ ({len(tasks_list)})",
            description=desc,
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_list, ephemeral=True)

    @app_commands.command(name="schedule_cancel", description="hủy bỏ lịch gửi của một embed")
    @app_commands.describe(name="chọn tên embed muốn hủy lịch từ danh sách")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def schedule_cancel(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        
        # Xóa toàn bộ task chứa tên embed này của server hiện tại
        result = await self.db_col.delete_many({
            "guild_id": str(interaction.guild.id), 
            "embed_name": name
        })
        
        if result.deleted_count > 0:
            await interaction.followup.send(f"{Emojis.BUOMA} đã hủy thành công `{result.deleted_count}` lịch chờ gửi của embed `{name}`.", ephemeral=True)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy lịch chờ nào của embed `{name}` nhe cậu.", ephemeral=True)

# Hàm setup để nạp cog
async def setup(bot: commands.Bot):
    cog = EmbedScheduler(bot)
    await bot.add_cog(cog)
    
    # Rút lệnh cũ ra và ghim vào cổng tổng /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn rác lệnh cũ
        bot.tree.remove_command("schedule")
        bot.tree.remove_command("schedule_list")
        bot.tree.remove_command("schedule_cancel")
        
        # Tiêm nhánh lệnh vào tháp bảo vệ tổng
        p_cmd.add_command(cog.schedule)
        p_cmd.add_command(cog.schedule_list)
        p_cmd.add_command(cog.schedule_cancel)
        print("[LOAD] Success: commands.embed.embed_scheduler (Connected to /p Master Shield)", flush=True)
    else:
        print("[LOAD] Warning: Không tìm thấy Master Group /p.", flush=True)
