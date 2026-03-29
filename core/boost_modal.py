# core/boost_modal.py
import discord


class RoleInputModal(discord.ui.Modal, title="Set Level Role"):

    role_input = discord.ui.TextInput(
        label="Role ID hoặc Role Mention",
        placeholder="Ví dụ: 123456789 hoặc @role",
        required=True,
        max_length=50
    )

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    async def on_submit(self, interaction: discord.Interaction):

        value = self.role_input.value.strip()

        role_id = None

        if value.startswith("<@&") and value.endswith(">"):
            role_id = value.replace("<@&", "").replace(">", "")

        elif value.isdigit():
            role_id = value

        if not role_id or not role_id.isdigit():
            await interaction.response.send_message(
                "Role không hợp lệ.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(int(role_id))

        if not role:
            await interaction.response.send_message(
                "Không tìm thấy role trong server.",
                ephemeral=True
            )
            return

        # =========================
        # FIX: CHECK ROLE HIERARCHY
        # =========================
        bot_member = interaction.guild.me

        if not bot_member or role >= bot_member.top_role:
            await interaction.response.send_message(
                "Role cao hơn bot, không thể sử dụng.",
                ephemeral=True
            )
            return

        await self.callback(interaction, role.id)


class DaysInputModal(discord.ui.Modal, title="Set Required Boost Days"):

    days_input = discord.ui.TextInput(
        label="Số ngày boost yêu cầu",
        placeholder="Ví dụ: 30",
        required=True,
        max_length=10
    )

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    async def on_submit(self, interaction: discord.Interaction):

        value = self.days_input.value.strip()

        if not value.isdigit():
            await interaction.response.send_message(
                "Days phải là số.",
                ephemeral=True
            )
            return

        days = int(value)

        if days <= 0:
            await interaction.response.send_message(
                "Days phải lớn hơn 0.",
                ephemeral=True
            )
            return

        await self.callback(interaction, days)
