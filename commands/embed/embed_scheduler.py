# commands/embed/embed_scheduler.py
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
        self.scheduler_loop.start()

    def cog_unload(self):
        self.scheduler_loop.cancel()

    # Vòng lặp "Trái tim" - Quét mỗi 60 giây
    @tasks.loop(seconds=60)
    async def scheduler_loop(self):
        # Lấy mốc thời gian hiện tại theo chuẩn Quốc tế tuyệt đối (Epoch)
        now = datetime.datetime.now().timestamp()
        
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
                
                # Xóa task sau khi nã đạn thành công
                await self.db_col.delete_one({"_id": task["_id"]})
            except Exception as e:
                print(f"[Scheduler Error] {e}", flush=True)

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

# Hàm setup để nạp cog
async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedScheduler(bot))
    print("[LOAD] Success: commands.embed.embed_scheduler", flush=True)
