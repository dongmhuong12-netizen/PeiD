import discord
from boost_modal import RoleInputModal, DaysInputModal
from boost_utils import validate_levels

LEVELS_PER_PAGE = 25
MAX_LEVELS = 99  # level 2 → 100


class BoosterLevelView(discord.ui.View):

    def __init__(self, guild, booster_role_id, levels, save_callback):
        super().__init__(timeout=600)

        self.guild = guild
        self.booster_role_id = booster_role_id
        self.save_callback = save_callback

        self.page = 0

        if not levels:
            self.levels = [
                {"role": None, "days": None}
                for _ in range(MAX_LEVELS)
            ]
        else:
            self.levels = levels.copy()

            if len(self.levels) < MAX_LEVELS:
                self.levels.extend(
                    [{"role": None, "days": None}]
                    for _ in range(MAX_LEVELS - len(self.levels))
                )


    # =========================
    # EMBED RENDER
    # =========================

    def build_embed(self):

        embed = discord.Embed(
            title="Booster Level Editor",
            color=0xf48fb1
        )

        booster_role = self.guild.get_role(self.booster_role_id)

        booster_text = booster_role.mention if booster_role else "Role chưa đặt"

        embed.description = (
            f"**Level 1 🔒**\n"
            f"Role: {booster_text}\n"
            f"Days: 0\n\n"
            f"Chỉnh các level bên dưới."
        )

        start = self.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        page_levels = self.levels[start:end]

        for i, lvl in enumerate(page_levels, start=start + 2):

            role = self.guild.get_role(lvl["role"]) if lvl["role"] else None

            if lvl["role"] and not role:
                lvl["role"] = None
                lvl["days"] = None

            role_text = role.mention if role else "Chưa đặt"
            days_text = lvl["days"] if lvl["days"] else "-"

            embed.add_field(
                name=f"Level {i}",
                value=f"Role: {role_text}\nDays: {days_text}",
                inline=False
            )

        max_page = (MAX_LEVELS - 1) // LEVELS_PER_PAGE

        embed.set_footer(
            text=f"Page {self.page + 1}/{max_page + 1}"
        )

        return embed


    # =========================
    # PAGE CONTROL
    # =========================

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button):

        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )


    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button):

        max_page = (MAX_LEVELS - 1) // LEVELS_PER_PAGE

        if self.page < max_page:
            self.page += 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )


    # =========================
    # EDIT ROLE
    # =========================

    @discord.ui.button(label="set role", style=discord.ButtonStyle.secondary, row=1)
    async def set_role(self, interaction: discord.Interaction, button):

        level_index = self.page * LEVELS_PER_PAGE

        async def callback(interaction, role_id):

            self.levels[level_index]["role"] = role_id

            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self
            )

        modal = RoleInputModal(callback)

        await interaction.response.send_modal(modal)


    # =========================
    # EDIT DAYS
    # =========================

    @discord.ui.button(label="set days", style=discord.ButtonStyle.secondary, row=1)
    async def set_days(self, interaction: discord.Interaction, button):

        level_index = self.page * LEVELS_PER_PAGE

        async def callback(interaction, days):

            self.levels[level_index]["days"] = days

            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self
            )

        modal = DaysInputModal(callback)

        await interaction.response.send_modal(modal)


    # =========================
    # CLEAR SLOT
    # =========================

    @discord.ui.button(label="clear", style=discord.ButtonStyle.danger, row=1)
    async def clear_level(self, interaction: discord.Interaction, button):

        level_index = self.page * LEVELS_PER_PAGE

        self.levels[level_index] = {
            "role": None,
            "days": None
        }

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )


    # =========================
    # SAVE
    # =========================

    @discord.ui.button(label="save", style=discord.ButtonStyle.primary, row=2)
    async def save_levels(self, interaction: discord.Interaction, button):

        valid, error = validate_levels(
            self.levels,
            self.booster_role_id
        )

        if not valid:

            await interaction.response.send_message(
                f"Không thể save: {error}",
                ephemeral=True
            )
            return

        await self.save_callback(self.levels)

        await interaction.response.send_message(
            "Đã lưu cấu hình booster level.",
            ephemeral=True
        )


    # =========================
    # CANCEL
    # =========================

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.danger, row=2)
    async def cancel_edit(self, interaction: discord.Interaction, button):

        await interaction.response.send_message(
            "Đã huỷ chỉnh sửa.",
            ephemeral=True
        )

        self.stop()
