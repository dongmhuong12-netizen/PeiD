import discord
import re

class RoleInputModal(discord.ui.Modal, title="Thiết lập Role cho Level"):
    def __init__(self, current_val: str, callback):
        super().__init__()
        self.callback = callback
        
        # Thêm TextInput động để hiển thị giá trị cũ
        self.role_input = discord.ui.TextInput(
            label="Role ID hoặc Role Mention",
            placeholder="Ví dụ: 123456789 hoặc @Booster-Role",
            default=str(current_val) if current_val else "",
            required=True,
            max_length=50
        )
        self.add_item(self.role_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.role_input.value.strip()
        
        # Sử dụng Regex để tách ID từ Mention <@&123...> hoặc lấy ID thuần
        role_id_match = re.search(r'\d+', value)
        if not role_id_match:
            return await interaction.response.send_message("❌ Role không hợp lệ (Không tìm thấy ID).", ephemeral=True)
            
        role_id = int(role_id_match.group())
        role = interaction.guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message("❌ Không tìm thấy role này trong server.", ephemeral=True)

        # KIỂM TRA HIERARCHY: Bot phải có quyền quản lý Role này
        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ Bot thiếu quyền 'Manage Roles' để thực hiện lệnh.", ephemeral=True)
            
        if role >= bot_member.top_role:
            return await interaction.response.send_message(
                f"❌ Role **{role.name}** cao hơn hoặc bằng cấp bậc của Bot. Hãy kéo Role của Bot lên cao hơn!", 
                ephemeral=True
            )

        # Trả kết quả về cho View xử lý tập trung
        await self.callback(interaction, role_id)


class DaysInputModal(discord.ui.Modal, title="Thiết lập Ngày yêu cầu"):
    def __init__(self, current_val: int, callback):
        super().__init__()
        self.callback = callback
        
        self.days_input = discord.ui.TextInput(
            label="Số ngày boost yêu cầu",
            placeholder="Ví dụ: 30 (cho mốc 1 tháng)",
            default=str(current_val) if current_val is not None else "",
            required=True,
            max_length=10
        )
        self.add_item(self.days_input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.days_input.value.strip()

        if not value.isdigit():
            return await interaction.response.send_message("❌ Vui lòng chỉ nhập số nguyên (Ví dụ: 30).", ephemeral=True)

        days = int(value)
        # Theo kế hoạch: Level 1 mặc định 0 ngày, các level sau phải > 0
        if days < 0:
            return await interaction.response.send_message("❌ Số ngày không được là số âm.", ephemeral=True)

        # Trả kết quả về cho View xử lý tập trung
        await self.callback(interaction, days)
