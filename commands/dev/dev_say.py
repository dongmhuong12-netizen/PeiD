import discord
import asyncio
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

    # ==========================================
    # LOGIC 1: TEXT COMMAND (!sy) - ZERO LATENCY
    # ==========================================
    @commands.command(name="sy", description="[PREMIUM] gửi tin nhắn thuần văn bản dưới danh nghĩa của bot có áp dụng bộ biến động")
    async def dev_say_text_cmd(self, ctx: commands.Context, *, text_content: str = None):
        # Ẩn danh thần tốc Zero-Latency: Xóa tin nhắn gọi lệnh của sếp NGAY LẬP TỨC ở background
        try:
            if ctx.message:
                asyncio.create_task(ctx.message.delete())
        except Exception:
            pass

        # Vòng kiểm duyệt bảo mật thời gian thực
        if not await self.has_premium_privilege(ctx.author.id):
            return await ctx.send(embed=self.get_unauthorized_embed(), delete_after=7)

        # Bắt lỗi khi sếp quên nhập nội dung
        if not text_content:
            return await ctx.send(
                f"{Emojis.HOICHAM} aree? cậu muốn lệnh được thực hiện thì hãy viết kèm nội dung sau `!sy` nhé.", 
                delete_after=7
            )

        try:
            # Bơm chuỗi ký tự qua cỗ máy Variable Engine để dịch toàn bộ biến tĩnh/động và Emoji
            processed_text = apply_variables(text_content, ctx.guild, ctx.author)

            # Thực thi nã đạn văn bản thẳng vào kênh. 
            # Logic kế thừa: Tự động reply nếu sếp có đính kèm reference, nếu không thì gửi bình thường.
            await ctx.send(content=processed_text, reference=ctx.message.reference)

        except Exception as e:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
                description=f"hệ thống gặp sự cố trong quá trình biên dịch biến số: `{str(e)}`",
                color=0xe6e2dd
            )
            await ctx.send(embed=embed_err, delete_after=10)

    # ==========================================
    # LOGIC 2: SLASH COMMAND (/sy) - TÀNG HÌNH 100%
    # ==========================================
    @app_commands.command(name="sy", description="[PREMIUM] gửi tin nhắn thuần văn bản dưới danh nghĩa của bot có áp dụng bộ biến động")
    @app_commands.describe(text_content="nhập nội dung lời nhắn (hỗ trợ đầy đủ biến văn bản và emoji hệ thống)")
    async def dev_say_slash_cmd(self, interaction: discord.Interaction, text_content: str):
        # Vòng kiểm duyệt bảo mật thời gian thực
        if not await self.has_premium_privilege(interaction.user.id):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        # Defer ẩn danh thần tốc để bảo vệ mạch kết nối với Discord
        await interaction.response.defer(ephemeral=True)

        try:
            # Bơm chuỗi ký tự qua cỗ máy Variable Engine để dịch toàn bộ biến tĩnh/động và Emoji
            processed_text = apply_variables(text_content, interaction.guild, interaction.user)

            # Thực thi nã đạn văn bản thẳng vào kênh hiện tại dưới danh nghĩa của Bot
            await interaction.channel.send(content=processed_text)

            # Phản hồi báo cáo ngầm hoàn thành nhiệm vụ cho người gọi lệnh
            await interaction.followup.send(f"{Emojis.BUOMA} gửi tin nhắn thành công.", ephemeral=True)

        except Exception as e:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
                description=f"hệ thống gặp sự cố trong quá trình biên dịch biến số: `{str(e)}`",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed_err, ephemeral=True)


async def setup(bot: commands.Bot):
    # Đăng ký Cog xử lý DB lên RAM trước. 
    # Khi Cog được nạp, cả Text Command (!sy) và Slash Command (/sy) sẽ tự động được kích hoạt an toàn.
    await bot.add_cog(DevSay(bot))
    print("[LOAD] Success: commands.dev.dev_say (Premium Unified Engine: !sy & /sy)", flush=True)
