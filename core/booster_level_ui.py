# core/booster_level_ui.py
import discord
from core.booster_storage import save_levels

LEVELS_PER_PAGE = 10
MAX_LEVELS = 100


class LevelSelect(discord.ui.Select):
    def __init__(self, view):
        self.view = view
        options = []

        start = view.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        for i in range(start, end):
            if i >= len(view.levels):
                break

            level = view.levels[i]

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
        self.view.selected_level = int(self.values[0])
        await self.view.refresh(interaction)


class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list, booster_role: int):
        super().__init__(timeout=None)

        self.guild_id = guild_id
        self.levels = levels
        self.booster_role = booster_role

        self.page = 0
        self.selected_level = 0

        # FORCE LEVEL 1
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

    async def refresh(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Bạn không có quyền dùng UI này.",
                    ephemeral=True
                )
            return

        if self.selected_level >= len(self.levels):
            self.selected_level = max(0, len(self.levels) - 1)

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

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
        await self.refresh(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        max_page = max(
            0,
            (len(self.levels) - 1) // LEVELS_PER_PAGE
        )
        if self.page < max_page:
            self.page += 1
        await self.refresh(interaction)

    @discord.ui.button(label="+", style=discord.ButtonStyle.success)
    async def add_page(self, interaction, button):
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

        await self.refresh(interaction)

    @discord.ui.button(label="Edit Role", style=discord.ButtonStyle.secondary)
    async def edit_role(self, interaction, button):
        index = self.selected_level

        class Modal(discord.ui.Modal, title="Set Role"):
            role = discord.ui.TextInput(
                label="Role ID hoặc mention"
            )

            async def on_submit(modal_self, i):
                val = modal_self.role.value.strip()

                if val.startswith("<@&"):
                    val = val[3:-1]

                if not val.isdigit():
                    await i.response.send_message(
                        "Role không hợp lệ",
                        ephemeral=True
                    )
                    return

                role_id = int(val)
                role_obj = i.guild.get_role(role_id)

                if not role_obj:
                    await i.response.send_message(
                        "Role không tồn tại",
                        ephemeral=True
                    )
                    return

                self.levels[index]["role"] = role_id
                await self.refresh(i)

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="Edit Days", style=discord.ButtonStyle.secondary)
    async def edit_days(self, interaction, button):
        index = self.selected_level

        if index == 0:
            await interaction.response.send_message(
                "Level 1 = 0 ngày",
                ephemeral=True
            )
            return

        class Modal(discord.ui.Modal, title="Set Days"):
            days = discord.ui.TextInput(label="Days")

            async def on_submit(modal_self, i):
                if not modal_self.days.value.isdigit():
                    await i.response.send_message(
                        "Days không hợp lệ",
                        ephemeral=True
                    )
                    return

                self.levels[index]["days"] = int(
                    modal_self.days.value
                )
                await self.refresh(i)

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="↑", style=discord.ButtonStyle.secondary)
    async def move_up(self, interaction, button):
        i = self.selected_level

        if i <= 1:
            return

        self.levels[i], self.levels[i - 1] = (
            self.levels[i - 1],
            self.levels[i]
        )
        self.selected_level -= 1
        await self.refresh(interaction)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.secondary)
    async def move_down(self, interaction, button):
        i = self.selected_level

        if i == 0:
            return

        if i >= len(self.levels) - 1:
            return

        self.levels[i], self.levels[i + 1] = (
            self.levels[i + 1],
            self.levels[i]
        )
        self.selected_level += 1
        await self.refresh(interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_level(self, interaction, button):
        if self.selected_level == 0:
            return

        self.levels.pop(self.selected_level)

        if self.selected_level >= len(self.levels):
            self.selected_level -= 1

        await self.refresh(interaction)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary)
    async def save_btn(self, interaction, button):
        prev_days = -1
        roles = set()

        for i, lvl in enumerate(self.levels):
            role = lvl.get("role")
            days = lvl.get("days")

            if role is None or days is None:
                await interaction.response.send_message(
                    "Thiếu dữ liệu",
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

            roles.add(role)

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

            prev_days = days

        # FIX BUG: save thật vào storage
        await save_levels(interaction.guild.id, self.levels)

        await interaction.response.send_message(
            "Đã lưu",
            ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction, button):
        await interaction.response.send_message(
            "Đã huỷ",
            ephemeral=True
        )
        self.stop()


async def open_booster_level_ui(
    bot,
    ctx,
    guild_id: int,
    levels: list,
    booster_role: int
):
    if not hasattr(bot, "_booster_ui_messages"):
        bot._booster_ui_messages = {}

    old_msg = bot._booster_ui_messages.get(guild_id)

    if old_msg:
        try:
            await old_msg.delete()
        except:
            pass

    view = BoosterLevelView(
        guild_id,
        levels,
        booster_role
    )

    if isinstance(ctx, discord.Interaction):
        msg = await ctx.followup.send(
            embed=view.build_embed(),
            view=view
        )
    else:
        msg = await ctx.send(
            embed=view.build_embed(),
            view=view
        )

    bot._booster_ui_messages[guild_id] = msg
