import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.embed_storage import load_embed, atomic_update_button
from core.cache_manager import get_raw, mark_dirty, update, save as force_save
from utils.emojis import Emojis

FILE_KEY = "verify_configs"

class VerifyGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="verify", description="hệ thống xác thực an ninh cao cấp (Double Counter Mode)")

    # =========================
    # INTERNAL HELPERS
    # =========================

    def _get_config(self, guild_id):
        """lấy cấu hình an ninh của server từ bộ não trung tâm"""
        db = get_raw(FILE_KEY)
        if not isinstance(db, dict):
            db = {}
            update(FILE_KEY, db)
            mark_dirty(FILE_KEY)
            
        # Mặc định văn phong yiyi cho nút bấm
        return db.get(str(guild_id), {
            "verified_role": None,
            "unverified_role": None,
            "success_log": None,
            "fail_log": None,
            "label": "Xác minh danh tính", # Tên nút cố định chuẩn yiyi
            "emoji": "🛡️"
        })

    def _save_config(self, guild_id, config):
        """lưu và chốt cấu hình vào database"""
        db = get_raw(FILE_KEY)
        db[str(guild_id)] = config
        update(FILE_KEY, db)
        mark_dirty(FILE_KEY)

    # =========================
    # LỆNH 1: SETUP ROLE KÉP
    # =========================

    @app_commands.command(name="role", description="thiết lập cặp role xác thực (Verified & Unverified)")
    @app_commands.describe(verified="role nhận được sau khi xác minh", unverified="role tạm thời cho mem mới")
    async def setup_roles(self, interaction: discord.Interaction, verified: discord.Role, unverified: discord.Role):
        await interaction.response.defer(ephemeral=True)
        
        config = self._get_config(interaction.guild.id)
        config["verified_role"] = str(verified.id)
        config["unverified_role"] = str(unverified.id)
        
        self._save_config(interaction.guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(
            f"{Emojis.YIYITIM} **an ninh:** hệ role đã khớp mạch!\n"
            f"• tạm trú: {unverified.mention}\n"
            f"• chính thức: {verified.mention}"
        )

    # =========================
    # LỆNH 2: SETUP NHẬT KÝ (LOGS)
    # =========================

    @app_commands.command(name="logs", description="thiết lập kênh nhật ký thành công và cảnh báo")
    @app_commands.describe(success="kênh báo success", alert="kênh báo trùng IP/Alt")
    async def setup_logs(self, interaction: discord.Interaction, success: discord.TextChannel, alert: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        config = self._get_config(interaction.guild.id)
        config["success_log"] = str(success.id)
        config["fail_log"] = str(alert.id)
        
        self._save_config(interaction.guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(
            f"{Emojis.YIYITIM} **an ninh:** kênh nhật ký đã sẵn sàng.\n"
            f"• success: {success.mention}\n"
            f"• alert: {alert.mention}"
        )

    # =========================
    # LỆNH 3: CẤY NÚT VÀO EMBED (APPLY)
    # =========================

    @app_commands.command(name="apply", description="kích hoạt cổng an ninh trên embed chỉ định")
    @app_commands.describe(embed_name="tên embed muốn gắn nút verify")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        config = self._get_config(guild_id)
        
        # 1. Validation Embed
        embed_data = await load_embed(guild_id, embed_name)
        if not embed_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} aree... không tìm thấy embed `{embed_name}`. sếp check lại kho lưu trữ nhé!")

        # 2. KIỀNG BA CHÂN: Validation toàn diện cấu hình
        missing = []
        if not config["verified_role"] or not config["unverified_role"]: missing.append("Hệ Role")
        if not config["success_log"] or not config["fail_log"]: missing.append("Hệ Nhật Ký")
        
        if missing:
            return await interaction.followup.send(
                f"{Emojis.HOICHAM} thiếu mảnh ghép! sếp cần hoàn tất: **{', '.join(missing)}** trước khi apply an ninh."
            )

        # 3. Data nút bấm mang DNA yiyi (Cố định Style)
        btn_data = {
            "type": "button",
            "style": "success",
            "label": "Xác minh thành viên", # Cố định theo yiyi style
            "emoji": "🛡️",
            "custom_id": "yiyi:verify:start", # ID thống nhất cho hệ thống
            "system": "verify"
        }
        
        # IT Pro logic: Cập nhật hoặc thêm mới không gây duplicate
        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:verify:start", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không thể cấy thêm mạch! embed này đã quá tải nút bấm.")
        
        await interaction.followup.send(f"{Emojis.YIYITIM} **an ninh:** đã kích hoạt thành công cổng Verify trên embed `{embed_name}`.")

    # =========================
    # LỆNH 4: TRẠNG THÁI (STATUS)
    # =========================

    @app_commands.command(name="status", description="soi trạng thái cổng an ninh hiện tại")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id)
        
        def get_obj(id, type_):
            if not id: return "❌"
            if type_ == "role": return interaction.guild.get_role(int(id)).mention if interaction.guild.get_role(int(id)) else "❌ (Đã xóa)"
            if type_ == "channel": return interaction.guild.get_channel(int(id)).mention if interaction.guild.get_channel(int(id)) else "❌ (Đã xóa)"

        embed = discord.Embed(title="🛡️ Security Status: Double Counter", color=0xf8bbd0)
        embed.add_field(name="Hệ Role", value=f"• Chờ: {get_obj(config['unverified_role'], 'role')}\n• Duyệt: {get_obj(config['verified_role'], 'role')}", inline=True)
        embed.add_field(name="Hệ Nhật Ký", value=f"• Success: {get_obj(config['success_log'], 'channel')}\n• Alert: {get_obj(config['fail_log'], 'channel')}", inline=True)
        embed.set_footer(text="DNA verify: yiyitim • status: online")
        
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "verify"), None)
        if existing: p_cmd.remove_command("verify")
        
        p_cmd.add_command(VerifyGroup())
        print("[load] verify_group: phase 1 integrated", flush=True)
