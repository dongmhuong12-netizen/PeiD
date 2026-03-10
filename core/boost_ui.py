import discord
from boost_modal import RoleInputModal, DaysInputModal
from boost_utils import validate_levels, move_level_up, move_level_down


LEVELS_PER_PAGE = 25


class BoosterLevelView(discord.ui.View):

    def __init__(self, guild, booster_role_id, levels, save_callback):
        super().__init__(timeout=600)

        self.guild = guild
        self.booster_role_id = booster_role_id
        self.levels = levels.copy()

        self.page = 0
        self.save_callback = save_callback


    # =========================
    # EMBED RENDER
    # =========================

    def build_embed(self):

        embed = discord.Embed(
            title="Booster Level Editor",
            color=0xf48fb1
        )

        start = self.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        page_levels = self.levels[start:end]

        if not page_levels:
            embed.description = "Chưa có level."
            return embed

        for i, lvl in enumerate(page_levels, start=start + 2):

            role = self.guild.get_role(lvl["role"])
            role_text = role.mention if role else "Role đã bị xoá"

            embed.add_field(
                name=f"Level {i}",
                value=f"Role: {role_text}\nDays: {lvl['days']}",
                inline=False
            )

        embed.set_footer(text=f"Page {self.page + 1}")

        return embed


    # =========================
    # PAGE CONTROL
    # =========================

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button):

        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(embed=self.build_embed(), view=self)


    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button):

        max_page = (len(self.levels) - 1) // LEVELS_PER_PAGE

        if self.page < max_page:
            self.page += 1

        await interaction.response.edit_message(embed=self.build_embed(), view=self)


    # =========================
    # ADD LEVEL
    # =========================

    @discord.ui.button(label="+", style=discord.ButtonStyle.success)
    async def add_level(self, interaction: discord.Interaction, button):

        if len(self.levels) >= 100:

            await interaction.response.send_message(
                "Đã đạt giới hạn 100 level.",
                ephemeral=True
            )
            return

        self.levels.append({
            "role": None,
            "days": None
        })

        await interaction.response.edit_message(embed=self.build_embed(), view=self)


    # =========================
    # SAVE
    # =========================

    @discord.ui.button(label="save", style=discord.ButtonStyle.primary, row=2)
    async def save_levels(self, interaction: discord.Interaction, button):

        valid, error = validate_levels(self.levels, self.booster_role_id)

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


    # =========================
    # EDIT ROLE
    # =========================

    async def edit_role(self, interaction, level_index):

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

    async def edit_days(self, interaction, level_index):

        async def callback(interaction, days):

            self.levels[level_index]["days"] = days

            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self
            )

        modal = DaysInputModal(callback)

        await interaction.response.send_modal(modal)
