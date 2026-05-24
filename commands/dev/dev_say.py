import discord
from discord import app_commands
from discord.ext import commands
from utils.emojis import Emojis
from core.variable_engine import apply_variables

class DevSay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Mạch kết nối an toàn tương thích với MongoDB Atlas Wrapper của peiD
        self.db_col = getattr(bot.db, "db", bot.db)["premium_users_sys"]

    async def has_premium_privilege(self, user_id: int) -> bool:
        """Kiểm toán quyền hạn thời gian thực: Boss tối cao hoặc User nằm trong sách trắng MongoDB"""
        if user_id == self.bot.boss_id:
            return True
        # Truy vết thực thể trong bộ nhớ đám mây Atlas
        record = await self.db_col.find_one({"user_id": str(user_id)})
        return record is not None

    def get_unauthorized_embed(self) -> discord.Embed:
        """Giao diện từ chối truy cập chuẩn văn phong mềm mại của yiyi và mã màu sếp chọn"""
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} không được rồi, xin lỗi cậu nhe..",
            description="lệnh này thuộc phân khu đặc cách Premium, chỉ có người sáng lập mới có thể sử dụng.",
            color=0xe6e2dd
        )
        return embed

# Định nghĩa lệnh dưới dạng thực thể độc lập để cấy vào Group cha động
@app_commands.command(name="say", description="[PREMIUM] gửi tin nhắn thuần văn bản dưới danh nghĩa của bot có áp dụng bộ biến động")
@app_commands.describe(text_content="nhập nội dung lời nhắn (hỗ trợ đầy đủ biến văn bản và emoji hệ thống)")
async def dev_say_cmd(interaction: discord.Interaction, text_content: str):
    # Khởi tạo điểm gọi Cog để tận dụng mạch DB kết nối sẵn
    cog = interaction.client.get_cog("DevSay")
    if not cog:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} nghẽn mạch cục bộ, không thể kết nối module.", ephemeral=True)

    # Vòng kiểm duyệt bảo mật thời gian thực
    if not await cog.has_premium_privilege(interaction.user.id):
        return await interaction.response.send_message(embed=cog.get_unauthorized_embed(), ephemeral=True)

    # Defer ẩn danh thần tốc để bảo vệ mạch kết nối với Discord
    await interaction.response.defer(ephemeral=True)

    try:
        # Bơm chuỗi ký tự qua cỗ máy Variable Engine để dịch toàn bộ biến tĩnh/động và Emoji
        processed_text = apply_variables(text_content, interaction.guild, interaction.user)

        # Thực thi nã đạn văn bản thẳng vào kênh hiện tại dưới danh nghĩa của Bot
        await interaction.channel.send(content=processed_text)

        # Phản hồi báo cáo ngầm hoàn thành nhiệm vụ cho người gọi lệnh
        await interaction.followup.send(f"{Emojis.BUOMA} đã truyền phát tin nhắn thành công.", ephemeral=True)

    except Exception as e:
        embed_err = discord.Embed(
            title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
            description=f"hệ thống gặp sự cố trong quá trình biên dịch biến số: `{str(e)}`",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_err, ephemeral=True)

async def setup(bot: commands.Bot):
    # Đăng ký Cog xử lý DB lên RAM trước
    await bot.add_cog(DevSay(bot))

    # [MULTI-IT PRO] Thuật toán kế thừa nghiêm ngặt:
    # Chỉ tìm và nhúng vào group /dev đã được file dev_emojis khởi tạo
    dev_group = None
    for cmd in bot.tree.get_commands():
        if cmd.name == "dev" and isinstance(cmd, app_commands.Group):
            dev_group = cmd
            break

    if dev_group:
        # Nhúng lệnh say vào chung nhà với dev_emojis
        dev_group.add_command(dev_say_cmd)
        print("[LOAD] Success: commands.dev.dev_say (Premium Text Engine Injected)", flush=True)
    else:
        print("[WARNING] Không tìm thấy group /dev từ dev_emojis. Lệnh say đang chờ nạp lại!", flush=True)
