import discord
from discord import app_commands
from discord.ext import commands
import time
from utils.emojis import Emojis

class PremiumGroup(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name="premium", description="[OWNER ONLY] Hệ thống quản lý và phân phối đặc quyền hệ thống")
        self.bot = bot
        # Mạch trích xuất cấu trúc DB chuẩn Industrial
        self.db_col = getattr(bot.db, "db", bot.db)["premium_users_sys"]

    def is_absolute_owner(self, interaction: discord.Interaction) -> bool:
        """Rào chắn bảo mật tối cao: Chỉ cho phép định danh Thực thể tối cao vượt qua"""
        return interaction.user.id == interaction.client.boss_id

    def get_owner_deny_embed(self) -> discord.Embed:
        """Giao diện chặn truy cập chuẩn văn phong yiyi dành riêng cho Owner"""
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} quyền hạn không đủ rồi nhe..",
            description="chỉ có sếp lớn chính chủ của *yiyi* mới cấu hình được mạch này thui nhe cậu.",
            color=0xe6e2dd
        )
        return embed

    @app_commands.command(name="grant", description="[OWNER ONLY] cấp đặc quyền sử dụng bộ lệnh Premium cho một người dùng")
    @app_commands.describe(user="chọn người dùng muốn cấp quyền đặc cách")
    async def premium_grant_cmd(self, interaction: discord.Interaction, user: discord.User):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        u_id_str = str(user.id)

        # Kiểm toán dữ liệu chống ghi đè trùng lặp bản ghi trên MongoDB Atlas
        existing = await self.db_col.find_one({"user_id": u_id_str})
        if existing:
            embed_dup = discord.Embed(
                title=f"{Emojis.YIYITIM} người này đã được cấp quyền rùi ạ",
                description=f"định danh user <@{u_id_str}> (`{u_id_str}`) đã nằm trong sách trắng đám mây từ trước.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_dup)

        # Thiết lập document lưu trữ cấu trúc lịch sử cấp quyền
        payload = {
            "user_id": u_id_str,
            "granted_by": str(interaction.user.id),
            "timestamp": int(time.time())
        }
        await self.db_col.insert_one(payload)

        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cấp quyền Premium thành công!",
            description=f"đã mở khóa mạch truyền tải dữ liệu đặc cách cho user {user.mention} (`{u_id_str}`) vĩnh viễn nhe sếp.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @app_commands.command(name="revoke", description="[OWNER ONLY] xóa bỏ đặc quyền Premium")
    @app_commands.describe(user="chọn người dùng muốn hủy bỏ quyền đặc cách")
    async def premium_revoke_cmd(self, interaction: discord.Interaction, user: discord.User):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        u_id_str = str(user.id)

        # Truy quét xác minh sự tồn tại của thực thể trước khi thực hiện quy trình hủy
        existing = await self.db_col.find_one({"user_id": u_id_str})
        if not existing:
            embed_none = discord.Embed(
                title=f"{Emojis.HOICHAM} không tìm thấy thực thể dữ liệu",
                description=f"user <@{u_id_str}> (`{u_id_str}`) vốn chưa từng được cấp quyền Premium aa.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_none)

        # [QUY TRÌNH CHẠY LÊN MONGO XOÁ BỎ HOÀN TOÀN DỨT ĐIỂM]
        # Triệt tiêu bản ghi vĩnh viễn ra khỏi bộ sưu tập đám mây đám mây, không để lại liên kết ma
        await self.db_col.delete_one({"user_id": u_id_str})

        embed_revoke_success = discord.Embed(
            title=f"{Emojis.BUOMA} thu hồi đặc quyền PREMIUM thành công",
            description=f"đã trục xuất triệt để user {user.mention} (`{u_id_str}`) ra khỏi sách trắng vĩnh viễn.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=revoke_success_success)

async def setup(bot: commands.Bot):
    # Khởi tạo và đăng ký trực tiếp Group vào Command Tree toàn cục của Bot
    bot.tree.add_command(PremiumGroup(bot))
    print("[LOAD] Success: commands.premium.premium_group (Premium Authority Engine Loaded)", flush=True)
