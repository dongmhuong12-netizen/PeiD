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
        """lấy cấu hình an ninh của server"""
        db = get_raw(FILE_KEY)
        if not isinstance(db, dict):
            db = {}
            update(FILE_KEY, db)
            mark_dirty(FILE_KEY)
            
        return db.get(str(guild_id), {
            "verified_role": None,
            "unverified_role": None,
            "success_log": None,
            "fail_log": None,
            "label": "Xác nhận thành viên",
            "emoji": "🛡️"
        })

    def _save_config(self, guild_id, config):
        """lưu và chốt cấu hình vào bộ não trung tâm"""
        db = get_raw(FILE_KEY)
        db[str(guild_id)] = config
        update(FILE_KEY, db)
        mark_dirty(FILE_KEY)

    # =========================
    # LỆNH 1: SETUP ROLE KÉP
    # =========================

    @app_commands.command(name="role", description="thiết lập hệ thống role xác thực kép")
    @app_commands.describe(verified="role sau khi veri thành công", unverified="role khi vừa vào (chưa veri)")
    async def setup_roles(self, interaction: discord.Interaction, verified: discord.Role, unverified: discord.Role):
        # Mạch Defer chuẩn IT Pro
        await interaction.response.defer(ephemeral=True)
        
        config = self._get_config(interaction.guild.id)
        config["verified_role"] = str(verified.id)
        config["unverified_role"] = str(unverified.id)
        
        self._save_config(interaction.guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(
            f"{Emojis.YIYITIM} **an ninh:** đã thiết lập cặp role:\n"
            f"• role chưa veri: {unverified.mention}\n"
            f"• role đã veri: {verified.mention}"
        )

    # =========================
    # LỆNH 2: SETUP KÊNH LOG LƯỠNG CỰC
    # =========================

    @app_commands.command(name="logs", description="thiết lập 2 kênh nhật ký an ninh")
    @app_commands.describe(success="kênh log veri thành công", alert="kênh log phát hiện clone/trùng ip")
    async def setup_logs(self, interaction: discord.Interaction, success: discord.TextChannel, alert: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        config = self._get_config(interaction.guild.id)
        config["success_log"] = str(success.id)
        config["fail_log"] = str(alert.id)
        
        self._save_config(interaction.guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(
            f"{Emojis.YIYITIM} **an ninh:** đã gán kênh log thành công ({success.mention}) và kênh cảnh báo alt/clone ({alert.mention})"
        )

    # =========================
    # LỆNH 3: TÙY CHỈNH NÚT
    # =========================

    @app_commands.command(name="button", description="tùy chỉnh giao diện nút bấm verify")
    @app_commands.describe(label="nhãn hiển thị trên nút", emoji="emoji hiển thị")
    async def set_button(self, interaction: discord.Interaction, label: str, emoji: str = "🛡️"):
        await interaction.response.defer(ephemeral=True)
        
        config = self._get_config(interaction.guild.id)
        config["label"] = label
        config["emoji"] = emoji
        
        self._save_config(interaction.guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(f"{Emojis.MATTRANG} giao diện nút đã cập nhật thành: {emoji} {label}")

    # =========================
    # LỆNH 4: CẤY NÚT VÀO EMBED (APPLY)
    # =========================

    @app_commands.command(name="apply", description="cấy hệ thống an ninh vào một embed thiết kế")
    @app_commands.describe(embed_name="tên embed muốn gắn nút verify")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        config = self._get_config(guild_id)
        
        # 1. Validation Embed
        embed_data = await load_embed(guild_id, embed_name)
        if not embed_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} aree... **yiyi** không tìm thấy embed `{embed_name}`. cậu kiểm tra lại bằng `/p embed show` nhé!")

        # 2. Validation Cấu hình
        if not config["verified_role"] or not config["unverified_role"]:
            return await interaction.followup.send(f"{Emojis.HOICHAM} sếp chưa thiết lập cặp role xác thực! hãy dùng `/p verify role` trước.")

        # 3. Data nút bấm mang ID định danh an ninh
        btn_data = {
            "type": "button",
            "style": "success",
            "label": config["label"],
            "emoji": config["emoji"],
            "custom_id": "yiyi:verify:high_sec",
            "system": "verify"
        }
        
        # IT Pro: Sử dụng logic Atomic của Storage để cấy nút không bị đè
        # Thử update nếu nút đã tồn tại, nếu False (chưa có) thì Add mới
        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:verify:high_sec", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không thể cấy nút! có vẻ embed này đã đạt giới hạn 25 nút bấm.")
        
        await interaction.followup.send(f"{Emojis.YIYITIM} **an ninh cấp cao:** đã cấy thành công mạch verify vào embed `{embed_name}`.")

    # =========================
    # LỆNH 5: CHECK TRẠNG THÁI
    # =========================

    @app_commands.command(name="status", description="kiểm tra cấu hình an ninh hiện tại")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id)
        
        # Lấy Object Role/Channel từ ID
        v_role = interaction.guild.get_role(int(config["verified_role"])) if config["verified_role"] else None
        u_role = interaction.guild.get_role(int(config["unverified_role"])) if config["unverified_role"] else None
        s_log = interaction.guild.get_channel(int(config["success_log"])) if config["success_log"] else None
        f_log = interaction.guild.get_channel(int(config["fail_log"])) if config["fail_log"] else None
        
        embed = discord.Embed(title="🛡️ Security System: Double Counter Mode", color=0xf8bbd0)
        embed.add_field(name="Hệ Role (Kép)", value=f"• Role Chưa Veri: {u_role.mention if u_role else '❌'}\n• Role Đã Veri: {v_role.mention if v_role else '❌'}", inline=False)
        embed.add_field(name="Hệ Log (Lưỡng Cực)", value=f"• Kênh Log Thành Công: {s_log.mention if s_log else '❌'}\n• Kênh Cảnh Báo Clone/Trùng IP: {f_log.mention if f_log else '❌'}", inline=False)
        embed.add_field(name="Giao Diện Nút", value=f"{config['emoji']} {config['label']}", inline=False)
        embed.set_footer(text="an ninh cấp độ quân sự đã sẵn sàng")
        
        await interaction.followup.send(embed=embed)

# =========================
# INJECTION
# =========================

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # [CẬP NHẬT] Dọn dẹp lệnh cũ nếu bị kẹt
        existing = next((c for c in p_cmd.commands if c.name == "verify"), None)
        if existing: p_cmd.remove_command("verify")
        
        p_cmd.add_command(VerifyGroup())
        print("[load] success: commands.verify.verify_group (High Security Phase 3)", flush=True)
    else:
        print("[error] không tìm thấy khung /p! đảm bảo command /p đã được khởi tạo.", flush=True)



