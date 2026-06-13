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
            description="chỉ có sếp Owner của *yiyi* mới cấu hình được mạch này thui",
            color=0xe6e2dd
        )
        return embed

    # =========================================================================
    # [THÊM MỚI] LỆNH 1: CẤU HÌNH TRẠNG THÁI KHÓA/MỞ MẠCH CÓ THAM SỐ BẬT/TẮT
    # =========================================================================
    @app_commands.command(name="config", description="[OWNER ONLY] Điều chỉnh bật/tắt trạng thái khóa mạch Premium tại máy chủ hiện tại")
    @app_commands.describe(trang_thai="Chọn trạng thái hoạt động của bộ khóa")
    @app_commands.choices(trang_thai=[
        app_commands.Choice(name="Bật (Khóa mạch hệ thống)", value="đóng"),
        app_commands.Choice(name="Tắt (Mở mạch hệ thống)", value="mở")
    ])
    async def premium_config_cmd(self, interaction: discord.Interaction, trang_thai: app_commands.Choice[str]):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        db_guilds = getattr(self.bot.db, "db", self.bot.db)["premium_server_configs"]
        
        await db_guilds.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"lock_status": trang_thai.value}},
            upsert=True
        )
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật cấu hình thành công",
            description=f"đã chuyển trạng thái hệ thống khóa tại máy chủ này thành: **{trang_thai.name}**.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    # =========================================================================
    # [THÊM MỚI] LỆNH 2: GÁN QUYỀN THỰC THI LỆNH RIÊNG BIỆT CHO 1 CÁ NHÂN TRONG SERVER
    # =========================================================================
    @app_commands.command(name="permit", description="[OWNER ONLY] Gán phân quyền thực thi bộ lệnh Premium cho một cá nhân tại máy chủ")
    @app_commands.describe(user="Chọn thành viên muốn cấp quyền sử dụng bộ lệnh")
    async def premium_permit_cmd(self, interaction: discord.Interaction, user: discord.User):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        db_server_users = getattr(self.bot.db, "db", self.bot.db)["premium_server_users"]
        u_id_str = str(user.id)
        g_id_str = str(interaction.guild.id)

        await db_server_users.update_one(
            {"guild_id": g_id_str, "user_id": u_id_str},
            {"$set": {
                "allowed_to_use": True, 
                "assigned_by": str(interaction.user.id), 
                "timestamp": int(time.time())
            }},
            upsert=True
        )

        embed = discord.Embed(
            title=f"{Emojis.BUOMA} gán quyền dùng lệnh thành công!",
            description=f"đã mở phân quyền thực thi bộ lệnh cho thành viên {user.mention} (`{u_id_str}`) tại máy chủ này thành công.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    # =========================================================================
    # GIỮ NGUYÊN BẢN 100% MÃ NGUỒN GỐC CỦA CẬU KHÔNG THAY ĐỔI LOGIC
    # =========================================================================
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
                description=f"định danh user <@{u_id_str}> (`{u_id_str}`) đã nằm trong phân khu đặc quyền từ trước.",
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
            description=f"đã mở khóa mạch truyền tải dữ liệu đặc cách cho user {user.mention} (`{u_id_str}`) thành công, từ giờ họ có thể dùng được các bộ lệnh thuộc phân quyền Premium.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @app_commands.command(name="revoke", description="[OWNER ONLY] xóa bỏ đặc quyền Premium")
    @app_commands.describe(user="chọn người dùng sở hữu premium muốn hủy bỏ quyền đặc cách")
    async def premium_revoke_cmd(self, interaction: discord.Interaction, user: str):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        u_id_str = user.strip()

        # Kiểm toán đầu vào phòng trường hợp cố tình nhập chuỗi phá hoại mạch thay vì chọn autocomplete
        if not u_id_str.isdigit():
            embed_invalid = discord.Embed(
                title=f"{Emojis.HOICHAM} định danh không hợp lệ",
                description="cậu vui lòng chọn đúng người dùng có trong danh sách gợi ý nhe.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_invalid)

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
            description=f"đã trục xuất triệt để user <@{u_id_str}> (`{u_id_str}`) ra khỏi sách trắng vĩnh viễn.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_revoke_success)

    @premium_revoke_cmd.autocomplete('user')
    async def premium_revoke_autocomplete(self, interaction: discord.Interaction, current: str):
        """Mạch lọc thông minh: Chỉ bóc tách và đề xuất các ID đang thực sự tồn tại trong DB Premium"""
        choices = []
        async for item in self.db_col.find({}):
            u_id = item["user_id"]
            # Đồng bộ cache lấy tên hiển thị trực quan cho sếp dễ chọn
            user_obj = self.bot.get_user(int(u_id))
            display_name = f"{user_obj.name} ({u_id})" if user_obj else f"User ID: {u_id}"
            
            if current.lower() in display_name.lower():
                choices.append(app_commands.Choice(name=display_name, value=u_id))
            
            if len(choices) >= 25:  # Giới hạn tối đa của Discord Autocomplete
                break
        return choices

    @app_commands.command(name="list", description="[OWNER ONLY] mở danh sách tất cả thực thể được cấp đặc quyền Premium")
    async def premium_list_cmd(self, interaction: discord.Interaction):
        if not self.is_absolute_owner(interaction):
            return await interaction.response.send_message(embed=self.get_owner_deny_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        premium_lines = []
        async for item in self.db_col.find({}):
            u_id = item["user_id"]
            g_by = item.get("granted_by", "Unknown")
            ts = item.get("timestamp", 0)

            # Đồng bộ cache lấy thông tin thực thể
            user_obj = self.bot.get_user(int(u_id))
            grantor_obj = self.bot.get_user(int(g_by)) if g_by.isdigit() else None

            user_fmt = f"<@{u_id}> (`{u_id}`)"
            grantor_fmt = f"<@{g_by}>" if grantor_obj else f"`{g_by}`"
            time_fmt = f"<t:{ts}:R>" if ts else "Không rõ"

            premium_lines.append(f"• {user_fmt}\n  └── Người cấp: {grantor_fmt} | update: {time_fmt}")

        embed_list = discord.Embed(
            title=f"{Emojis.BUOMA} danh sách thực thể Premium",
            color=0xe6e2dd
        )

        if premium_lines:
            text_content = "\n".join(premium_lines)
            # Phòng vệ giới hạn ký tự 4096 của description embed tránh tràn bộ nhớ đệm
            if len(text_content) > 4000:
                text_content = text_content[:3900] + "\n...và một số thực thể Premium khác."
            embed_list.description = text_content
        else:
            embed_list.description = "Hiện tại chưa có người dùng nào được cấy đặc quyền Premium hệ thống đâu a."

        embed_list.set_footer(text="Hệ thống quản lý phân phối đặc quyền của yiyi")
        await interaction.followup.send(embed=embed_list)

async def setup(bot: commands.Bot):
    # Khởi tạo và đăng ký trực tiếp Group vào Command Tree toàn cục của Bot
    bot.tree.add_command(PremiumGroup(bot))
    print("[LOAD] Success: commands.premium.premium_group (Premium Authority Engine Loaded)", flush=True)
