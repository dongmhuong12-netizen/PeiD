import discord
from core.booster_storage import save_levels

LEVELS_PER_PAGE = 10
MAX_LEVELS = 100


class LevelSelect(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = []

        start = parent_view.page * LEVELS_PER_PAGE
        end = min(start + LEVELS_PER_PAGE, MAX_LEVELS)

        for i in range(start, end):
            if i >= len(parent_view.levels):
                level = {"role": None, "days": None}
            else:
                level = parent_view.levels[i]

            role = level.get("role")
            days = level.get("days")

            role_text = f"ID: {role}" if role else "chưa edit"
            days_text = str(days) if days is not None else "chưa edit"

            options.append(
                discord.SelectOption(
                    label=f"Level {i + 1}",
                    description=f"{role_text} | Days: {days_text}",
                    value=str(i)
                )
            )

        super().__init__(
            placeholder="Chọn level để chỉnh",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_level = int(self.values[0])
        await interaction.response.defer()
        await self.parent_view.refresh(interaction)


class PageIndicatorButton(discord.ui.Button):
    def __init__(self, current: int, total: int):
        super().__init__(
            label=f"Page {current}/{total}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=1
        )


class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list, booster_role: int):
        super().__init__(timeout=None)

        self.guild_id = guild_id
        self.booster_role = booster_role
        self.page = 0
        self.selected_level = 0
        self.message = None

        self.levels = [lvl.copy() for lvl in levels] if levels else []

        if not self.levels:
            self.levels.append({
                "role": booster_role,
                "days": 0
            })
        else:
            self.levels[0]["role"] = booster_role
            self.levels[0]["days"] = 0

        self.ensure_page_slots(0)
        self.update_components()

    def ensure_page_slots(self, page: int):
        required = min((page + 1) * LEVELS_PER_PAGE, MAX_LEVELS)

        while len(self.levels) < required:
            self.levels.append({
                "role": None,
                "days": None
            })

    def get_total_pages(self):
        return max(1, (len(self.levels) - 1) // LEVELS_PER_PAGE + 1)

    def build_embed(self):
        embed = discord.Embed(
            title="Booster Level Editor",
            color=0xf48fb1
        )

        start = self.page * LEVELS_PER_PAGE
        end = min(start + LEVELS_PER_PAGE, MAX_LEVELS)

        for i in range(start, end):
            lvl = self.levels[i]

            role = lvl.get("role")
            days = lvl.get("days")

            role_text = f"<@&{role}>" if role else "chưa edit"

            if i == 0:
                days_text = "0"
            else:
                days_text = str(days) if days is not None else "chưa edit"

            embed.add_field(
                name=f"Level {i + 1}",
                value=f"Role: {role_text}\nDays: {days_text}",
                inline=False
            )

        embed.set_footer(
            text=f"Page {self.page + 1}/{self.get_total_pages()}"
        )
        return embed

    def update_components(self):
        self.clear_items()

        self.add_item(LevelSelect(self))

        total_pages = self.get_total_pages()

        self.add_item(self.prev_page)
        self.add_item(PageIndicatorButton(self.page + 1, total_pages))
        self.add_item(self.add_page)
        self.add_item(self.next_page)

        self.add_item(self.edit_role)
        self.add_item(self.edit_days)

        self.add_item(self.move_up)
        self.add_item(self.move_down)
        self.add_item(self.delete_level)

        self.add_item(self.save_btn)
        self.add_item(self.cancel_btn)

    async def refresh(self, interaction: discord.Interaction = None):
        self.ensure_page_slots(self.page)

        if self.selected_level >= len(self.levels):
            self.selected_level = max(0, len(self.levels) - 1)

        self.update_components()
        embed = self.build_embed()

        target_message = self.message
        if interaction and getattr(interaction, "message", None):
            target_message = interaction.message

        if target_message:
            await target_message.edit(embed=embed, view=self)
            self.message = target_message

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button):
        if self.page == 0:
            await interaction.response.send_message(
                "Đã đến trang đầu tiên",
                ephemeral=True
            )
            return

        self.page -= 1
        self.selected_level = self.page * LEVELS_PER_PAGE

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="+", style=discord.ButtonStyle.success, row=1)
    async def add_page(self, interaction: discord.Interaction, button):
        max_page = (MAX_LEVELS // LEVELS_PER_PAGE) - 1
        next_page = self.page + 1

        if next_page > max_page:
            await interaction.response.send_message(
                "Đã đạt tối đa 100 level.",
                ephemeral=True
            )
            return

        self.ensure_page_slots(next_page)
        self.page = next_page
        self.selected_level = self.page * LEVELS_PER_PAGE

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button):
        total_pages = self.get_total_pages()

        if self.page >= total_pages - 1:
            await interaction.response.send_message(
                "Đã đến trang cuối cùng",
                ephemeral=True
            )
            return

        self.page += 1
        self.selected_level = self.page * LEVELS_PER_PAGE

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Edit Role", style=discord.ButtonStyle.secondary, row=2)
    async def edit_role(self, interaction: discord.Interaction, button):
        index = self.selected_level
        parent = self

        class Modal(discord.ui.Modal, title="Set Role"):
            role = discord.ui.TextInput(label="Role ID hoặc mention")

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                val = modal_self.role.value.strip()

                if val.startswith("<@&") and val.endswith(">"):
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

    @discord.ui.button(label="Edit Days", style=discord.ButtonStyle.secondary, row=2)
    async def edit_days(self, interaction: discord.Interaction, button):
        index = self.selected_level
        parent = self

        if index == 0:
            await interaction.response.send_message(
                "Level 1 luôn = 0 ngày",
                ephemeral=True
            )
            return

        class Modal(discord.ui.Modal, title="Set Days"):
            days = discord.ui.TextInput(label="Days")

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                value = modal_self.days.value.strip()

                if not value.isdigit():
                    await modal_interaction.response.send_message(
                        "Days không hợp lệ",
                        ephemeral=True
                    )
                    return

                parent.levels[index]["days"] = int(value)

                await modal_interaction.response.defer()
                await parent.refresh()

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="↑", style=discord.ButtonStyle.secondary, row=3)
    async def move_up(self, interaction: discord.Interaction, button):
        i = self.selected_level

        if i <= 1:
            await interaction.response.defer()
            return

        self.levels[i], self.levels[i - 1] = self.levels[i - 1], self.levels[i]
        self.selected_level -= 1

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.secondary, row=3)
    async def move_down(self, interaction: discord.Interaction, button):
        i = self.selected_level

        if i == 0 or i >= len(self.levels) - 1:
            await interaction.response.defer()
            return

        self.levels[i], self.levels[i + 1] = self.levels[i + 1], self.levels[i]
        self.selected_level += 1

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, row=3)
    async def delete_level(self, interaction: discord.Interaction, button):
        if self.selected_level == 0:
            await interaction.response.defer()
            return

        if self.selected_level < len(self.levels):
            self.levels.pop(self.selected_level)

        if self.page > 0 and self.page * LEVELS_PER_PAGE >= len(self.levels):
            self.page -= 1

        self.selected_level = min(
            self.selected_level,
            len(self.levels) - 1
        )

        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary, row=4)
    async def save_btn(self, interaction: discord.Interaction, button):
        prev_days = -1
        roles = set()
        cleaned_levels = []

        for i, lvl in enumerate(self.levels):
            role = lvl.get("role")
            days = lvl.get("days")

            if role is None and days is None:
                continue

            if role is None or days is None:
                await interaction.response.send_message(
                    f"Level {i + 1} thiếu dữ liệu",
                    ephemeral=True
                )
                return

            if role in roles:
                await interaction.response.send_message(
                    "Role bị trùng",
                    ephemeral=True
                )
                return

            if role == self.booster_role and i != 0:
                await interaction.response.send_message(
                    "Role trùng booster role",
                    ephemeral=True
                )
                return

            if i == 0 and days != 0:
                await interaction.response.send_message(
                    "Level 1 phải = 0",
                    ephemeral=True
                )
                return

            if days <= prev_days:
                await interaction.response.send_message(
                    "Days phải tăng dần",
                    ephemeral=True
                )
                return

            roles.add(role)
            prev_days = days
            cleaned_levels.append({
                "role": role,
                "days": days
            })

        await save_levels(interaction.guild.id, cleaned_levels)

        await interaction.response.send_message(
            "Đã lưu cấu hình booster level",
            ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=4)
    async def cancel_btn(self, interaction: discord.Interaction, button):
        try:
            target_message = self.message or interaction.message
            if target_message:
                await target_message.edit(view=None)
        except Exception:
            pass

        await interaction.response.send_message(
            "Đã huỷ",
            ephemeral=True
        )
        self.stop()
