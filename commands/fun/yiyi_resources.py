import discord
from discord import app_commands
from discord.ext import commands
import time

# [INDUSTRIAL IMPORTS]
from core.state import State
from utils.emojis import Emojis

# =============================
# RESOURCE ENGINE (MAX STATS)
# =============================

@app_commands.command(name="resources", description="báo cáo chi tiết tài nguyên và sức khỏe Cloud Atlas")
async def resources_cmd(interaction: discord.Interaction):
    """
    Truy vấn dbStats trực tiếp từ MongoDB Atlas và báo cáo thông số kỹ thuật.
    """
    # Defer sớm để tránh lỗi 10062 khi MongoDB phản hồi chậm
    await interaction.response.defer(ephemeral=False)
    
    db = getattr(State.bot, "db", None)
    if not db:
        return await interaction.followup.send(content=f"{Emojis.HOICHAM} yiyi không tìm thấy mạch nối tới não bộ MongoDB. Sếp kiểm tra lại kết nối nhé.")

    try:
        # 1. Đo mạch Latency (Độ trễ)
        start_time = time.perf_counter()
        # Lệnh dbStats: Bốc toàn bộ chỉ số vận hành của Database
        stats = await db.command("dbStats")
        end_time = time.perf_counter()
        
        latency = (end_time - start_time) * 1000 # Chuyển sang ms

        # 2. Bóc tách linh kiện (Atomic Extraction)
        db_name = stats.get("db", "Unknown")
        collections = stats.get("collections", 0)
        objects = stats.get("objects", 0) # Tổng số bản ghi (documents)
        
        # Chuyển đổi Bytes -> MB (Industrial Standard)
        data_size = stats.get("dataSize", 0) / (1024 * 1024)
        storage_size = stats.get("storageSize", 0) / (1024 * 1024)
        index_size = stats.get("indexSize", 0) / (1024 * 1024)
        avg_obj_size = stats.get("avgObjSize", 0) / 1024 # KB

        # 3. Tạo Embed báo cáo (Industrial Design)
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} báo cáo tài nguyên hệ thống peiD",
            description=(
                f"trạng thái kết nối với **MongoDB Atlas** hiện đang rất ổn định.\n"
                f"mọi dữ liệu đang được đồng bộ hóa thời gian thực."
            ),
            color=0xf8bbd0
        )
        
        # --- Thông tin Database ---
        embed.add_field(name="🧬 Database", value=f"`{db_name}`", inline=True)
        embed.add_field(name="📶 Latency", value=f"`{latency:.2f}ms`", inline=True)
        embed.add_field(name="📂 Collections", value=f"`{collections}`", inline=True)
        
        # --- Thông tin Dung lượng ---
        embed.add_field(
            name="📊 Quản lý lưu trữ", 
            value=(
                f"• Dữ liệu thô: **{data_size:.2f} MB**\n"
                f"• Thực tế chiếm dụng: **{storage_size:.2f} MB**\n"
                f"• Chỉ mục (Indexes): **{index_size:.2f} MB**"
            ), 
            inline=False
        )
        
        # --- Thông tin Bản ghi ---
        embed.add_field(name="📝 Tổng bản ghi", value=f"**{objects:,}** docs", inline=True)
        embed.add_field(name="📏 Kích thước trung bình", value=f"**{avg_obj_size:.2f} KB**/doc", inline=True)
        
        embed.set_footer(text=f"yiyi resource monitor • chuẩn multi-it industrial • version 2.0")
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"[resources error] {e}", flush=True)
        await interaction.followup.send(content=f"{Emojis.HOICHAM} **yiyi** bị 'nghẽn mạch' khi đọc Cloud Atlas. (Lỗi: `{type(e).__name__}`)")

# =============================
# INJECTION (MODULE LOADER)
# =============================

async def setup(bot: commands.Bot):
    """
    Hàm setup để nạp extension và tiêm lệnh vào nhóm 'yiyi'.
    """
    # Tìm nhóm lệnh 'yiyi' hiện có trong hệ thống
    yiyi_group = bot.tree.get_command("yiyi")
    
    if yiyi_group and isinstance(yiyi_group, app_commands.Group):
        # Phòng thủ: Gỡ lệnh cũ nếu đã tồn tại trước khi nạp bản mới
        existing = next((c for c in yiyi_group.commands if c.name == "resources"), None)
        if existing:
            yiyi_group.remove_command("resources")
            
        # Tiêm lệnh resources vào nhóm /yiyi
        yiyi_group.add_command(resources_cmd)
        print("[load] success: commands.fun.yiyi_resources (Multi-IT Edition)", flush=True)
