import discord
import re

# ==============================
# ROLE INPUT MODAL
# ==============================

class RoleInputModal(discord.ui.Modal, title="Thiết lập Role cho Level"):
    def __init__(self, current_val: str, callback):
        super().__init__()
        self.callback = callback
        
        # TextInput động hiển thị giá trị hiện tại để Admin dễ sửa
        self.role_input = discord.ui.TextInput(
            label="Role ID hoặc Role Mention",
            placeholder="Ví dụ: 123456789 hoặc @Role_Booster",
            default=str(current_val) if current_val else "",
            required=True,
            max_length=50
        )
        self.add_item(self.role_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.role_input.value.strip()
        
        # GIỮ NGUYÊN LOGIC: Dùng Regex để tách ID từ <@&ID> hoặc lấy ID thuần
        role_id_match = re.search(r'\d+', value)
        if not role_id_match:
            return await interaction.response.send_message("❌ Role không hợp lệ (Không tìm thấy ID số).", ephemeral=True)
            
        try:
            role_id = int(role_id_match.group())
            role = interaction.guild.get_role(role_id)

            if not role:
                return await interaction.response.send_message("❌ Không tìm thấy role này trong server hiện tại.", ephemeral=True)

            # KIỂM TRA HIERARCHY (QUAN TRỌNG): Bot phải đủ quyền quản lý Role này
            bot_member = interaction.guild.me
            if not bot_member.guild_permissions.manage_roles:
                return await interaction.response.send_message("❌ Bot thiếu quyền 'Manage Roles'. Hãy cấp quyền cho Bot!", ephemeral=True)
                
            if role >= bot_member.top_role:
                return await interaction.response.send_message(
                    f"❌ Role **{role.name}** cao hơn cấp bậc của Bot. Hãy kéo Role của Bot lên trên Role này!", 
                    ephemeral=True
                )

            # Trả kết quả về cho View xử lý tập trung (Refresh UI)
            await self.callback(interaction, role_id)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {str(e)}", ephemeral=True)

# ==============================
# DAYS INPUT MODAL
# ==============================

class DaysInputModal(discord.ui.Modal, title="Thiết lập Ngày yêu cầu"):
    def __init__(self, current_val: int, callback):
        super().__init__()
        self.callback = callback
        
        self.days_input = discord.ui.TextInput(
            label="Số ngày boost yêu cầu",
            placeholder="Ví dụ: 30",
            default=str(current_val) if current_val is not None else "",
            required=True,
            max_length=10
        )
        self.add_item(self.days_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.days_input.value.strip()

        if not value.isdigit():
            return await interaction.response.send_message("❌ Vui lòng chỉ nhập số nguyên dương.", ephemeral=True)

        days = int(value)
        
        # Chặn số âm để tránh làm hỏng logic so sánh trong Engine
        if days < 0:
            return await interaction.response.send_message("❌ Số ngày không được là số âm.", ephemeral=True)

        # Trả kết quả về cho View
        await self.callback(interaction, days)
