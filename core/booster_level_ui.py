import discord
from core.booster_storage import save_levels

LEVELS_PER_PAGE = 10
MAX_LEVELS = 100


class LevelSelect(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = []

        start = parent_view.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        for i in range(start, end):
            if i >= len(parent_view.levels):
                break

            level = parent_view.levels[i]

            role_text = (
                f"<@&{level.get('role')}>"
                if level.get("role")
                else "chưa đặt"
            )
            days_text = (
                str(level.get("days"))
                if level.get("days") is not None
                else "chưa đặt"
            )

            options.append(
                discord.SelectOption(
                    label=f"Level {i + 1}",
                    description=f"{role_text} | {days_text}",
                    value=str(i)
                )
            )

        super().__init__(
            placeholder="Chọn level",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_level = int(self.values[0])
        await self.parent_view.refresh(interaction)


class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list, booster_role: int):
        super().__init__(timeout=None)

        self.guild_id = guild_id
        self.levels = levels
        self.booster_role = booster_role
        self.page = 0
        self.selected_level = 0
        self.message = None

        if not self.levels:
            self.levels.append({
                "role": booster_role,
                "days": 0
            })
        else:
            self.levels[0]["role"] = booster_role
            self.levels[0]["days"] = 0

        self.update_components()

    def build_embed(self):
        embed = discord.Embed(
            title="Booster Level Editor",
            color=0xf48fb1
        )

        start = self.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        for i in range(start, end):
            if i >= len(self.levels):
                break

            lvl = self.levels[i]
            role = lvl.get("role")
            days = lvl.get("days")

            role_text = f"<@&{role}>" if role else "chưa đặt"
            days_text = str(days) if days is not None else "chưa đặt"

            embed.add_field(
                name=f"Level {i + 1}",
                value=f"Role: {role_text}\nDays: {days_text}",
                inline=False
            )

        total_pages = max(
            1,
            (len(self.levels) - 1) // LEVELS_PER_PAGE + 1
        )
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages}")
        return embed

    def update_components(self):
        self.clear_items()

        self.add_item(LevelSelect(self))
        self.add_item(self.prev_page)
        self.add_item(self.next_page)
        self.add_item(self.add_page)

        self.add_item(self.edit_role)
        self.add_item(self.edit_days)

        self.add_item(self.move_up)
        self.add_item(self.move_down)
        self.add_item(self.delete_level)

        self.add_item(self.save_btn)
        self.add_item(self.cancel_btn)

    async def refresh(self, interaction: discord.Interaction = None):
        if self.selected_level >= len(self.levels):
            self.selected_level = max(0, len(self.levels) - 1)

        self.update_components()
        embed = self.build_embed()

        target_message = self.message

        if interaction and getattr(interaction, "message", None):
            target_message = interaction.message

        if target_message:
            try:
                await target_message.edit(embed=embed, view=self)
                self.message = target_message
            except Exception:
                pass

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button):
        max_page = max(0, (len(self.levels) - 1) // LEVELS_PER_PAGE)
        if self.page < max_page:
            self.page += 1
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="+", style=discord.ButtonStyle.success)
    async def add_page(self, interaction: discord.Interaction, button):
        if len(self.levels) >= MAX_LEVELS:
            await interaction.response.send_message(
                "Đã đạt 100 level.",
                ephemeral=True
            )
            return

        for _ in range(LEVELS_PER_PAGE):
            if len(self.levels) >= MAX_LEVELS:
                break
            self.levels.append({
                "role": None,
                "days": None
            })

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Edit Role", style=discord.ButtonStyle.secondary)
    async def edit_role(self, interaction: discord.Interaction, button):
        index = self.selected_level
        parent = self

        class Modal(discord.ui.Modal, title="Set Role"):
            role = discord.ui.TextInput(label="Role ID hoặc mention")

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                val = modal_self.role.value.strip()

                if val.startswith("<@&"):
                    val = val[3:-1]

                if not val.isdigit():
                    await modal_interaction.response.send_message(
                        "Role không hợp lệ",
                        ephemeral=True
                    )
                    return

                role_id = int(val)
                role_obj = modal_interaction.guild.get_role(role_id)

                if not role_obj:
                    await modal_interaction.response.send_message(
                        "Role không tồn tại",
                        ephemeral=True
                    )
                    return

                parent.levels[index]["role"] = role_id
                await modal_interaction.response.defer()
                await parent.refresh()

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="Edit Days", style=discord.ButtonStyle.secondary)
    async def edit_days(self, interaction: discord.Interaction, button):
        index = self.selected_level
        parent = self

        if index == 0:
            await interaction.response.send_message(
                "Level 1 = 0 ngày",
                ephemeral=True
            )
            return

        class Modal(discord.ui.Modal, title="Set Days"):
            days = discord.ui.TextInput(label="Days")

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                if not modal_self.days.value.isdigit():
                    await modal_interaction.response.send_message(
                        "Days không hợp lệ",
                        ephemeral=True
                    )
                    return

                parent.levels[index]["days"] = int(modal_self.days.value)
                await modal_interaction.response.defer()
                await parent.refresh()

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="↑", style=discord.ButtonStyle.secondary)
    async def move_up(self, interaction: discord.Interaction, button):
        i = self.selected_level
        if i <= 1:
            await interaction.response.defer()
            return

        self.levels[i], self.levels[i - 1] = self.levels[i - 1], self.levels[i]
        self.selected_level -= 1

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.secondary)
    async def move_down(self, interaction: discord.Interaction, button):
        i = self.selected_level

        if i == 0 or i >= len(self.levels) - 1:
            await interaction.response.defer()
            return

        self.levels[i], self.levels[i + 1] = self.levels[i + 1], self.levels[i]
        self.selected_level += 1

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_level(self, interaction: discord.Interaction, button):
        if self.selected_level == 0:
            await interaction.response.defer()
            return

        self.levels.pop(self.selected_level)

        if self.selected_level >= len(self.levels):
            self.selected_level -= 1

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary)
    async def save_btn(self, interaction: discord.Interaction, button):
        prev_days = -1
        roles = set()

        for i, lvl in enumerate(self.levels):
            role = lvl.get("role")
            days = lvl.get("days")

            if role is None or days is None:
                await interaction.response.send_message("Thiếu dữ liệu", ephemeral=True)
                return

            if role in roles:
                await interaction.response.send_message("Role bị trùng", ephemeral=True)
                return

            if role == self.booster_role and i != 0:
                await interaction.response.send_message("Role trùng booster role", ephemeral=True)
                return

            roles.add(role)

            if i == 0 and days != 0:
                await interaction.response.send_message("Level 1 phải = 0", ephemeral=True)
                return

            if days <= prev_days:
                await interaction.response.send_message("Days phải tăng dần", ephemeral=True)
                return

            prev_days = days

        await save_levels(interaction.guild.id, self.levels)
        await interaction.response.send_message("Đã lưu", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("Đã huỷ", ephemeral=True)
        self.stop()
