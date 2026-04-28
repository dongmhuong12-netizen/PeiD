import discord
import re
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# ==============================
# ROLE INPUT MODAL
# ==============================

class RoleInputModal(discord.ui.Modal, title="thiết lập role cho level"):
    def __init__(self, current_val: str, callback):
        super().__init__()
        self.callback = callback
        
        # TextInput động hiển thị giá trị hiện tại
        self.role_input = discord.ui.TextInput(
            label="role id hoặc role mention",
            placeholder="ví dụ: 123456789 hoặc @role_booster",
            default=str(current_val) if current_val else "",
            required=True,
            max_length=50
        )
        self.add_item(self.role_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.role_input.value.strip()
        
        # GIỮ NGUYÊN LOGIC: Dùng Regex để tách ID
        role_id_match = re.search(r'\d+', value)
        if not role_id_match:
            # 1. TEXT THUẦN (Theo yêu cầu)
            return await interaction.response.send_message("role không hợp lệ. hãy đảm bảo rằng cậu nhập id đúng của server", ephemeral=True)
            
        try:
            role_id = int(role_id_match.group())
            role = interaction.guild.get_role(role_id)

            if not role:
                # 2. CHUYỂN SANG EMBED
                embed = discord.Embed(
                    description=f"{Emojis.HOICHAM} có vẻ role này đã bị tác động bởi manager hoặc đã bị xoá khỏi server, xin hãy nhập lại id khác",
                    color=0xf8bbd0
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            # KIỂM TRA HIERARCHY (QUAN TRỌNG): Bot phải đủ quyền quản lý Role này
            bot_member = interaction.guild.me
            if not bot_member.guild_permissions.manage_roles:
                # 3. CHUYỂN SANG EMBED + KHUNG CODE QUYỀN
                embed = discord.Embed(
                    description=f"{Emojis.HOICHAM} yiyi vẫn chưa có `quyền quản lí vai trò` để có thể setup, hãy cấp quyền cho yiyi trước khi setup nhé",
                    color=0xf8bbd0
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
                
            if role >= bot_member.top_role:
                # 4. CHUYỂN SANG EMBED
                embed = discord.Embed(
                    description=f"{Emojis.HOICHAM} hmm..? có một lỗi nhỏ ở đây. hãy đảm bảo role của yiyi phải luôn cao hơn role setup nhé",
                    color=0xf8bbd0
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            # Trả kết quả về cho View xử lý tập trung
            await self.callback(interaction, role_id)
            
        except Exception as e:
            # [VÁ LỖI] Kiểm tra trạng thái interaction để tránh crash task ngầm
            if not interaction.response.is_done():
                embed = discord.Embed(
                    description=f"{Emojis.HOICHAM} phát sinh lỗi: `{str(e)}`",
                    color=0xf8bbd0
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                print(f"[MODAL ERROR] {e}", flush=True)

# ==============================
# DAYS INPUT MODAL
# ==============================

class DaysInputModal(discord.ui.Modal, title="thiết lập ngày yêu cầu"):
    def __init__(self, current_val: int, callback):
        super().__init__()
        self.callback = callback
        
        self.days_input = discord.ui.TextInput(
            label="số ngày boost yêu cầu",
            placeholder="ví dụ: 30",
            default=str(current_val) if current_val is not None else "",
            required=True,
            max_length=10
        )
        self.add_item(self.days_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.days_input.value.strip()

        if not value.isdigit():
            # 5. TEXT THUẦN (Theo yêu cầu)
            return await interaction.response.send_message("hãy chỉ nhập số nguyên dương. ví dụ :`30`", ephemeral=True)

        days = int(value)
        
        # Chặn số âm để tránh làm hỏng logic so sánh trong Engine
        if days < 0:
            # 6. TEXT THUẦN (Theo yêu cầu)
            return await interaction.response.send_message("số ngày không được phép là số âm", ephemeral=True)

        try:
            # Trả kết quả về cho View
            await self.callback(interaction, days)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"phát sinh lỗi: `{str(e)}`", ephemeral=True)
