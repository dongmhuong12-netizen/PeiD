import discord
import hashlib
from core.cache_manager import get_raw, mark_dirty, update, save as force_save
from utils.emojis import Emojis
import os

CONFIG_KEY = "verify_configs"
FINGERPRINT_DB = "verify_fingerprints"

class VerifySystem:
    """
    [HIGH-SECURITY ENGINE]
    Hệ thống xử lý hậu cần xác thực. Đảm bảo logic:
    Check IP -> Báo cáo Log -> Hoán đổi Role.
    """

    @staticmethod
    def _get_linked_accounts(guild: discord.Guild, fingerprint: str, current_user_id: int):
        """[Multi-IT] Tìm tất cả các tài khoản trùng dấu vân tay trong server"""
        fp_db = get_raw(FINGERPRINT_DB)
        guild_data = fp_db.get(str(guild.id), {})
        
        links = []
        for uid, stored_fp in guild_data.items():
            if stored_fp == fingerprint and int(uid) != current_user_id:
                member = guild.get_member(int(uid))
                links.append(f"{member.mention} (`{uid}`)" if member else f"User thoát: `{uid}`")
        return links

    @staticmethod
    async def handle_interaction(interaction: discord.Interaction):
        """Mạch xử lý khi user nhấn nút 'Xác minh' trên Embed"""
        
        # Đồng bộ custom_id với verify_group.py
        if interaction.data.get("custom_id") != "yiyi:verify:start":
            return False

        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        db = get_raw(CONFIG_KEY)
        config = db.get(str(guild.id))

        # 1. Kiểm tra kiềng ba chân (Lớp bảo vệ cuối)
        if not config or not config.get("verified_role") or not config.get("success_log"):
            await interaction.followup.send(f"{Emojis.HOICHAM} Hệ thống chưa sẵn sàng. Admin cần hoàn tất setup.", ephemeral=True)
            return True

        # 2. Tạo URL Verify (Tích hợp Secret từ môi trường)
        # Giả định render URL đã được setup ở .env như sếp nói
        base_url = os.getenv("VERIFY_WEB_URL", "https://yiyi-verify.bot")
        verify_url = f"{base_url}/auth?user={interaction.user.id}&guild={guild.id}"

        # 3. Phản hồi dẫn tới Web (Văn phong yiyi)
        embed = discord.Embed(
            description=f"{Emojis.YIYITIM} **Cổng an ninh:** Vui lòng nhấn vào nút bên dưới để tiến hành xác minh danh tính và nhận quyền truy cập.",
            color=0xf8bbd0
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Mở trang xác minh", url=verify_url, emoji="🔗"))
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        return True

    @staticmethod
    async def process_verification_success(guild: discord.Guild, member: discord.Member, ip_address: str):
        """
        [BACKEND LOGIC] Hàm này sẽ được gọi khi Web xác nhận Success.
        Thực hiện Double Counter và gán Role.
        """
        db = get_raw(CONFIG_KEY)
        config = db.get(str(guild.id))
        if not config: return

        # 1. Tạo Fingerprint từ IP thật (do Web gửi về)
        fingerprint = hashlib.md5(ip_address.encode()).hexdigest()[:12]
        
        # 2. Check Trùng IP (Alert Logic)
        linked_accs = VerifySystem._get_linked_accounts(guild, fingerprint, member.id)
        
        # Lấy kênh log
        success_log = guild.get_channel(int(config.get("success_log", 0)))
        alert_log = guild.get_channel(int(config.get("fail_log", 0)))

        if linked_accs:
            # TRƯỜNG HỢP: TRÙNG IP (ALERT)
            if alert_log:
                embed = discord.Embed(title="🚨 CẢNH BÁO: PHÁT HIỆN TRÙNG IP", color=discord.Color.orange())
                embed.add_field(name="Đối tượng", value=f"{member.mention} (`{member.id}`)", inline=False)
                embed.add_field(name="Địa chỉ IP", value=f"`{ip_address}`", inline=True)
                embed.add_field(name="Dấu vân tay", value=f"`{fingerprint}`", inline=True)
                embed.add_field(name="Các tài khoản liên quan", value="\n".join(linked_accs), inline=False)
                
                # Nút Check Profile (Sẽ xử lý ở Phase 6)
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Check Profile", custom_id=f"yiyi:secret:check:{member.id}", style=discord.ButtonStyle.secondary))
                
                await alert_log.send(embed=embed, view=view)
            
            # Sếp dặn: Trùng IP thì giữ nguyên Role Unverified, không gán Role mới
            return False

        # TRƯỜNG HỢP: XÁC MINH SẠCH (SUCCESS)
        v_role = guild.get_role(int(config["verified_role"]))
        u_role = guild.get_role(int(config["unverified_role"]))

        try:
            if v_role: await member.add_roles(v_role, reason="Yiyi Security: Success")
            if u_role and u_role in member.roles: await member.remove_roles(u_role, reason="Yiyi Security: Verified")

            # Lưu vào Fingerprint DB
            fp_db = get_raw(FINGERPRINT_DB)
            if str(guild.id) not in fp_db: fp_db[str(guild.id)] = {}
            fp_db[str(guild.id)][str(member.id)] = fingerprint
            update(FINGERPRINT_DB, fp_db)
            mark_dirty(FINGERPRINT_DB)

            if success_log:
                embed = discord.Embed(title="✅ XÁC MINH THÀNH CÔNG", color=discord.Color.green())
                embed.description = f"Thành viên {member.mention} đã vượt qua cổng an ninh.\nIP: `{ip_address}`"
                await success_log.send(embed=embed)
            
            return True
        except Exception:
            return False

    @staticmethod
    async def on_member_join(member: discord.Member):
        """Tự động gán role unverified cho mem mới join (Chuẩn IT)"""
        db = get_raw(CONFIG_KEY)
        config = db.get(str(member.guild.id))
        if config and config.get("unverified_role"):
            role = member.guild.get_role(int(config["unverified_role"]))
            if role:
                try:
                    await member.add_roles(role, reason="Yiyi Security: Chờ xác minh")
                except: pass
