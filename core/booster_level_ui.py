import discord


# =========================
# MODAL: EDIT DAYS
# =========================

class EditDaysModal(discord.ui.Modal):

    def __init__(self, view, index: int):
        super().__init__(title="Chỉnh số ngày boost")

        self.view = view
        self.index = index

        self.days = discord.ui.TextInput(
            label="Số ngày boost",
            placeholder="Ví dụ: 30",
            required=True
        )

        self.add_item(self.days)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            value = int(self.days.value)

            if value < 0:
                raise ValueError

            self.view.levels[self.index]["days"] = value

            await self.view.refresh(interaction)

        except ValueError:

            await interaction.response.send_message(
                "Số ngày không hợp lệ.",
                ephemeral=True
            )


# =========================
# MODAL: EDIT ROLE
# =========================

class EditRoleModal(discord.ui.Modal):

    def __init__(self, view, index: int):
        super().__init__(title="Chỉnh role")

        self.view = view
        self.index = index

        self.role = discord.ui.TextInput(
            label="Role ID hoặc mention",
            required=True
        )

        self.add_item(self.role)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild
        value = self.role.value.strip()

        if value.startswith("<@&") and value.endswith(">"):
            value = value[3:-1]

        if not value.isdigit():
            await interaction.response.send_message(
                "Role không hợp lệ.",
                ephemeral=True
            )
            return

        role = guild.get_role(int(value))

        if not role:
            await interaction.response.send_message(
                "Role không tồn tại.",
                ephemeral=True
            )
            return

        self.view.levels[self.index]["role"] = role.id

        await self.view.refresh(interaction)


# =========================
# SELECT LEVEL
# =========================

class LevelSelect(discord.ui.Select):

    def __init__(self, view):

        self.view = view

        options = []

        for i, level in enumerate(view.levels):

            role = level.get("role")
            days = level.get("days")

            role_text = f"<@&{role}>" if role else "chưa đặt"
            days_text = str(days) if days is not None else "chưa đặt"

            options.append(
                discord.SelectOption(
                    label=f"Level {i+1}",
                    description=f"{role_text} | {days_text}",
                    value=str(i)
                )
            )

        super().__init__(
            placeholder="Chọn level để chỉnh",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):

        self.view.selected_level = int(self.values[0])

        await self.view.refresh(interaction)


# =========================
# MAIN VIEW
# =========================

class BoosterLevelView(discord.ui.View):

    def __init__(self, guild_id: int, levels: list):

        super().__init__(timeout=None)

        self.guild_id = guild_id
        self.levels = levels
        self.selected_level = 0
        self.message = None

        self.update_components()

    # =========================
    # BUILD EMBED
    # =========================

    def build_embed(self):

        embed = discord.Embed(
            title="Booster Level Editor",
            description="Chỉnh hệ thống cấp bậc booster.",
            color=0xf48fb1
        )

        for i, level in enumerate(self.levels):

            role = level.get("role")
            days = level.get("days")

            role_text = f"<@&{role}>" if role else "chưa đặt"
            days_text = str(days) if days is not None else "chưa đặt"

            embed.add_field(
                name=f"Level {i+1}",
                value=f"Role: {role_text}\nDays: {days_text}",
                inline=False
            )

        return embed

    # =========================
    # UPDATE COMPONENTS
    # =========================

    def update_components(self):

        self.clear_items()

        if self.levels:
            self.add_item(LevelSelect(self))

        self.add_item(self.edit_role)
        self.add_item(self.edit_days)
        self.add_item(self.delete_level)

        self.add_item(self.move_up)
        self.add_item(self.move_down)

        self.add_item(self.add_level)

        self.add_item(self.save_btn)
        self.add_item(self.cancel_btn)

    async def refresh(self, interaction):

        self.update_components()

        embed = self.build_embed()

        if interaction.response.is_done():

            await interaction.message.edit(
                embed=embed,
                view=self
            )

        else:

            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

    # =========================
    # BUTTONS
    # =========================

    @discord.ui.button(label="Edit Role", style=discord.ButtonStyle.secondary)
    async def edit_role(self, interaction: discord.Interaction, button):

        if not self.levels:
            await interaction.response.send_message(
                "Chưa có level.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            EditRoleModal(self, self.selected_level)
        )

    @discord.ui.button(label="Edit Days", style=discord.ButtonStyle.secondary)
    async def edit_days(self, interaction: discord.Interaction, button):

        if not self.levels:
            await interaction.response.send_message(
                "Chưa có level.",
                ephemeral=True
            )
            return

        # Level 1 không được sửa days
        if self.selected_level == 0:

            await interaction.response.send_message(
                "Level 1 luôn có Days = 0.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            EditDaysModal(self, self.selected_level)
        )

    @discord.ui.button(label="Delete Level", style=discord.ButtonStyle.secondary)
    async def delete_level(self, interaction: discord.Interaction, button):

        if len(self.levels) <= 1:

            await interaction.response.send_message(
                "Không thể xoá Level 1.",
                ephemeral=True
            )
            return

        self.levels.pop(self.selected_level)

        if self.selected_level >= len(self.levels):
            self.selected_level = len(self.levels) - 1

        await self.refresh(interaction)

    @discord.ui.button(label="↑ Move Up", style=discord.ButtonStyle.secondary)
    async def move_up(self, interaction: discord.Interaction, button):

        i = self.selected_level

        if i <= 1:
            await interaction.response.send_message(
                "Không thể di chuyển Level 1.",
                ephemeral=True
            )
            return

        self.levels[i], self.levels[i-1] = self.levels[i-1], self.levels[i]

        self.selected_level -= 1

        await self.refresh(interaction)

    @discord.ui.button(label="↓ Move Down", style=discord.ButtonStyle.secondary)
    async def move_down(self, interaction: discord.Interaction, button):

        i = self.selected_level

        if i >= len(self.levels) - 1:
            await interaction.response.send_message(
                "Level đã ở dưới cùng.",
                ephemeral=True
            )
            return

        self.levels[i], self.levels[i+1] = self.levels[i+1], self.levels[i]

        self.selected_level += 1

        await self.refresh(interaction)

    @discord.ui.button(label="Add Level", style=discord.ButtonStyle.success)
    async def add_level(self, interaction: discord.Interaction, button):

        self.levels.append({
            "role": None,
            "days": None
        })

        self.selected_level = len(self.levels) - 1

        await self.refresh(interaction)

    # =========================
    # SAVE / CANCEL
    # =========================

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary)
    async def save_btn(self, interaction: discord.Interaction, button):

        prev_days = -1

        for i, level in enumerate(self.levels):

            role = level.get("role")
            days = level.get("days")

            if role is None:

                await interaction.response.send_message(
                    "Level chưa có role.",
                    ephemeral=True
                )
                return

            if days is None:

                await interaction.response.send_message(
                    "Level chưa có số ngày boost.",
                    ephemeral=True
                )
                return

            if i == 0 and days != 0:

                await interaction.response.send_message(
                    "Level 1 phải có Days = 0.",
                    ephemeral=True
                )
                return

            if days <= prev_days:

                await interaction.response.send_message(
                    "Days của level phải tăng dần.",
                    ephemeral=True
                )
                return

            prev_days = days

        interaction.client.dispatch(
            "booster_level_save",
            interaction.guild.id,
            self.levels
        )

        await interaction.response.send_message(
            "Đã lưu cấu hình Booster Level.",
            ephemeral=True
        )

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button):

        await interaction.response.send_message(
            "Huỷ chỉnh sửa.",
            ephemeral=True
        )

        self.stop()
