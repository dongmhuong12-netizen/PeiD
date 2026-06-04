#commands/dev/dev_say.py
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
    # LOGIC 1: TEXT COMMAND (!sy) - ZERO LATENCY + MEDIA SUPPORT
    # ==========================================
    @commands.command(name="sy", description="[PREMIUM] gửi tin nhắn và file dưới danh nghĩa của bot")
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

        # [NÂNG CẤP 1] Bắt lỗi khi sếp KHÔNG nhập chữ VÀ CŨNG KHÔNG gửi file
        if not text_content and not ctx.message.attachments:
            return await ctx.send(
                f"{Emojis.HOICHAM} aree? cậu muốn lệnh được thực hiện thì hãy viết nội dung hoặc gửi kèm ảnh/file nhé.", 
                delete_after=7
            )

        try:
            # [NÂNG CẤP 1] Chặn lỗi Variable Engine nếu sếp chỉ gửi ảnh (text_content = None)
            processed_text = apply_variables(text_content, ctx.guild, ctx.author) if text_content else None

            # [NÂNG CẤP 1] Trích xuất và đóng gói toàn bộ file đính kèm
            files = []
            for attachment in ctx.message.attachments:
                files.append(await attachment.to_file())

            # Thực thi nã đạn văn bản và Media thẳng vào kênh. 
            # Logic kế thừa: Tự động reply nếu sếp có đính kèm reference.
            await ctx.send(content=processed_text, files=files, reference=ctx.message.reference)

        except Exception as e:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
                description=f"hệ thống gặp sự cố trong quá trình xử lý: `{str(e)}`",
                color=0xe6e2dd
            )
            await ctx.send(embed=embed_err, delete_after=10)

    # ==========================================
    # LOGIC 2: SLASH COMMAND (/sy) - MULTI-FILE + TÀNG HÌNH 100% + CLEAN UI
    # ==========================================
    @app_commands.command(name="sy", description="[PREMIUM] gửi tin nhắn và file dưới danh nghĩa của bot")
    @app_commands.describe(
        text_content="nhập nội dung lời nhắn (hỗ trợ đầy đủ biến văn bản và emoji hệ thống)",
        file1="đính kèm file, ảnh, video, gif (tùy chọn)",
        file2="đính kèm file, ảnh, video, gif (tùy chọn)",
        file3="đính kèm file, ảnh, video, gif (tùy chọn)"
    )
    async def dev_say_slash_cmd(
        self, 
        interaction: discord.Interaction, 
        text_content: str = None,
        file1: discord.Attachment = None,
        file2: discord.Attachment = None,
        file3: discord.Attachment = None
    ):
        # Vòng kiểm duyệt bảo mật thời gian thực
        if not await self.has_premium_privilege(interaction.user.id):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        # [NÂNG CẤP 1] Bắt lỗi khi sếp để trống toàn bộ mặt trận
        if not text_content and not file1 and not file2 and not file3:
            return await interaction.response.send_message(
                f"{Emojis.HOICHAM} aree? cậu cần nhập nội dung hoặc đính kèm ít nhất 1 file nhé.", 
                ephemeral=True
            )

        # [NÂNG CẤP 2] Defer tàng hình: báo cho API biết đã nhận lệnh, "Yiyi đang suy nghĩ..." chỉ mình sếp thấy
        await interaction.response.defer(ephemeral=True)

        try:
            # [NÂNG CẤP 1] Biên dịch biến số (bỏ qua nếu chỉ gửi file)
            processed_text = apply_variables(text_content, interaction.guild, interaction.user) if text_content else None

            # [NÂNG CẤP 1] Nạp đạn Media từ các khe cắm (Lọc các ô trống)
            files = []
            for f in [file1, file2, file3]:
                if f is not None:
                    files.append(await f.to_file())

            # Thực thi nã đạn văn bản/ảnh thẳng vào kênh hiện tại dưới danh nghĩa của Bot
            await interaction.channel.send(content=processed_text, files=files)

            # [NÂNG CẤP 3] Tự hủy dấu vết: Xóa sạch dòng chữ "Yiyi đang suy nghĩ..." trên màn hình sếp
            await interaction.delete_original_response()

        except Exception as e:
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} lỗi truyền tải mạch văn bản",
                description=f"hệ thống gặp sự cố trong quá trình xử lý: `{str(e)}`",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed_err, ephemeral=True)


async def setup(bot: commands.Bot):
    # Đăng ký Cog xử lý DB lên RAM trước. 
    # Khi Cog được nạp, cả Text Command (!sy) và Slash Command (/sy) sẽ tự động được kích hoạt an toàn.
    await bot.add_cog(DevSay(bot))
    print("[LOAD] Success: commands.dev.dev_say (Premium Unified Engine: !sy & /sy)", flush=True)
