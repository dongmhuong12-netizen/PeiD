import discord
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

    # Đổi sang dạng text command với tên "sy"
    @commands.command(name="sy", description="[PREMIUM] gửi tin nhắn thuần văn bản dưới danh nghĩa của bot có áp dụng bộ biến động")
    async def dev_say_cmd(self, ctx: commands.Context, *, text_content: str):
        # Vòng kiểm duyệt bảo mật thời gian thực
        if not await self.has_premium_privilege(ctx.author.id):
            return await ctx.send(embed=self.get_unauthorized_embed(), delete_after=7)

        # Ẩn danh thần tốc: Xóa tin nhắn gọi lệnh của sếp để giấu dấu vết
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        try:
            # Bơm chuỗi ký tự qua cỗ máy Variable Engine để dịch toàn bộ biến tĩnh/động và Emoji
            processed_text = apply_variables(text_content, ctx.guild, ctx.author)

            # Thực thi nã đạn văn bản thẳng vào kênh hiện tại dưới danh nghĩa của Bot
            await ctx.send(content=processed_text)

            # Phản hồi báo cáo ngầm hoàn thành nhiệm vụ (Tự động bốc hơi sau 3s thay cho ephemeral)
            await ctx.send(f"{Emojis.BUOMA} gửi tin nhắn thành công.", delete_after=3)

        except Exception as e:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
                description=f"hệ thống gặp sự cố trong quá trình biên dịch biến số: `{str(e)}`",
                color=0xe6e2dd
            )
            await ctx.send(embed=embed_err, delete_after=10)

async def setup(bot: commands.Bot):
    # Đăng ký Cog xử lý DB lên RAM trước
    await bot.add_cog(DevSay(bot))
    print("[LOAD] Success: commands.dev.dev_say (Premium Text Engine Injected - sy command)", flush=True)
