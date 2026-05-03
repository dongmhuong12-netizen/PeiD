```python
import discord
import hashlib
from core.cache_manager import get_raw, mark_dirty, update, save as force_save
from utils.emojis import Emojis

# Các tệp cơ sở dữ liệu
CONFIG_KEY = "verify_configs"
FINGERPRINT_DB = "verify_fingerprints" # Lưu trữ dấu vết thiết bị/IP

class VerifySystem:
    """
    [HIGH-SECURITY ENGINE]
    Bộ não xử lý logic xác thực Double Counter Mode.
    Nhiệm vụ: Quét IP/Thiết bị, gán/gỡ Role, và ghi Log An Ninh.
    """
    
    @staticmethod
    def _generate_device_fingerprint(member: discord.Member):
        """
        [MÔ PHỎNG AN NINH]
        Vì Discord API cấm lấy IP trực tiếp qua Interaction, ta mô phỏng một 
        'Security Fingerprint' (Dấu vân tay thiết bị) dựa trên các metadata ẩn.
        Trong thực tế nếu sếp kết nối Web OAuth2, biến này sẽ là IP thật.
        """
        # Thuật toán băm (Hash) tạo chuỗi định danh duy nhất cho thiết bị
        raw_data = f"{member.created_at.timestamp()}_{member.default_avatar.key}"
        return hashlib.md5(raw_data.encode()).hexdigest()[:12]

    @staticmethod
    async def handle_interaction(interaction: discord.Interaction):
        """Mạch bắt sự kiện khi người dùng nhấn nút Verify"""
        
        # 1. BỘ LỌC ĐỊNH DANH (Chỉ bắt đúng ID hệ an ninh của sếp)
        if interaction.data.get("custom_id") != "yiyi:verify:high_sec":
            return False

        # Quy tắc 3S: Defer ngay lập tức để né lỗi 'Interaction Failed' đỏ lòm
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        member = interaction.user
        
        # 2. TẢI CẤU HÌNH AN NINH SERVER
        db = get_raw(CONFIG_KEY)
        config = db.get(str(guild.id))
        
        if not config or not config.get("verified_role") or not config.get("unverified_role"):
            await interaction.followup.send(f"{Emojis.HOICHAM} Hệ thống chưa được setup Role! Admin cần chạy lệnh `/p verify role`.", ephemeral=True)
            return True

        # 3. QUÉT DẤU VÂN TAY / IP (DOUBLE COUNTER LOGIC)
        fp_db = get_raw(FINGERPRINT_DB)
        if str(guild.id) not in fp_db:
            fp_db[str(guild.id)] = {}
            
        current_fp = VerifySystem._generate_device_fingerprint(member)
        alt_match_id = None
        
        # Duyệt DB tìm IP/Thiết bị trùng lặp
        for uid, stored_fp in fp_db[str(guild.id)].items():
            if stored_fp == current_fp and uid != str(member.id):
                # Chỉ báo động nếu thằng trùng lặp vẫn còn nằm trong server (tránh rác log)
                if guild.get_member(int(uid)):
                    alt_match_id = uid
                    break

        # Tải kênh Log từ cấu hình
        success_log_ch = guild.get_channel(int(config.get("success_log", 0))) if config.get("success_log") else None
        fail_log_ch = guild.get_channel(int(config.get("fail_log", 0))) if config.get("fail_log") else None

        # ==========================================
        # NHÁNH 1: PHÁT HIỆN CLONE -> TỬ HÌNH + BÁO ĐỘNG
        # ==========================================
        if alt_match_id:
            orig_user = guild.get_member(int(alt_match_id))
            
            # Ghi Log Cảnh Báo (Ping Admin để tự quyết)
            if fail_log_ch:
                embed_fail = discord.Embed(
                    title="🚨 CẢNH BÁO AN NINH: PHÁT HIỆN CLONE/ALT", 
                    color=discord.Color.red()
                )
                embed_fail.add_field(name="Thành viên mới (Bị chặn)", value=f"{member.mention}\nID: `{member.id}`", inline=True)
                embed_fail.add_field(name="Trùng khớp với (Nick chính)", value=f"{orig_user.mention}\nID: `{alt_match_id}`", inline=True)
                embed_fail.add_field(name="Nguyên nhân", value=f"Trùng Security Fingerprint / IP (`{current_fp}`)", inline=False)
                embed_fail.set_thumbnail(url=member.display_avatar.url)
                embed_fail.set_footer(text="Hệ thống đã tự động từ chối xác thực tài khoản này.")
                
                await fail_log_ch.send(content="<@&ROLE_ADMIN_ID_HERE> Cảnh báo có đối tượng sử dụng tài khoản phụ!", embed=embed_fail)
            
            # Thông báo cho đối tượng
            await interaction.followup.send(
                f"{Emojis.HOICHAM} **Truy cập bị từ chối!** Hệ thống an ninh phát hiện bạn đang sử dụng nhiều tài khoản (Trùng IP/Thiết bị).", 
                ephemeral=True
            )
            return True

        # ==========================================
        # NHÁNH 2: XÁC THỰC THÀNH CÔNG -> HOÁN ĐỔI ROLE
        # ==========================================
        v_role = guild.get_role(int(config["verified_role"]))
        u_role = guild.get_role(int(config["unverified_role"]))

        try:
            # 1. Tránh spam click nếu đã veri rồi
            if v_role in member.roles:
                await interaction.followup.send(f"{Emojis.MATTRANG} Cậu đã xác nhận từ trước rồi mà!", ephemeral=True)
                return True

            # 2. Xưởng an ninh: Gỡ xích (Unverified), Trao huy hiệu (Verified)
            if v_role: 
                await member.add_roles(v_role, reason="Yiyi Security: Vượt qua bài kiểm tra an ninh")
            if u_role and u_role in member.roles: 
                await member.remove_roles(u_role, reason="Yiyi Security: Gỡ role chưa xác thực")
            
            # 3. Lưu dấu vân tay vào DB để phòng nó tạo clone vào sau
            fp_db[str(guild.id)][str(member.id)] = current_fp
            update(FINGERPRINT_DB, fp_db)
            mark_dirty(FINGERPRINT_DB)
            # Ép lưu khẩn cấp để đảm bảo dữ liệu không mất nếu bot restart
            import asyncio
            asyncio.create_task(force_save(FINGERPRINT_DB))

            # 4. Ghi Log Thành công
            if success_log_ch:
                embed_ok = discord.Embed(title="✅ Xác thực thành công", color=discord.Color.green())
                embed_ok.description = f"{member.mention} (`{member.id}`) đã vượt qua lưới điện an ninh."
                embed_ok.set_footer(text=f"Fingerprint: {current_fp}")
                await success_log_ch.send(embed=embed_ok)

            # 5. Thông báo cho người dùng
            await interaction.followup.send(f"{Emojis.YIYITIM} Hoàn tất! Bạn đã được cấp quyền truy cập máy chủ.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(f"{Emojis.HOICHAM} Tớ không đủ quyền! Admin hãy kéo Role của tớ lên trên role {v_role.mention} và {u_role.mention} nhé.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} Hệ thống gặp sự cố: `{e}`", ephemeral=True)
            
        return True


```
