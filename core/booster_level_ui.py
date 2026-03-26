# booster_level_ui.py
import discord

LEVELS_PER_PAGE = 10
MAX_PAGES = 10

# =========================
# SELECT LEVEL
# =========================
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
            role_text = f"<@&{level.get('role')}>" if level.get("role") else "chưa đặt"
            days_text = str(level.get("days")) if level.get("days") is not None else "chưa đặt"

            options.append(
                discord.SelectOption(
                    label=f"Level {i+1}",
                    description=f"{role_text} | {days_text}",
                    value=str(i)
                )
            )

        super().__init__(placeholder="Chọn level", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_level = int(self.values[0])
        await self.view.refresh(interaction)

# =========================
# BOOSTER LEVEL VIEW
# =========================
class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.levels = levels
        self.page = 0
        self.max_page = max(0, (len(levels)-1)//LEVELS_PER_PAGE)
        self.selected_level = 0
        self.message = None
        self.update_components()

    # =========================
    # EMBED
    # =========================
    def build_embed(self):
        embed = discord.Embed(title="Booster Level Editor", color=0xf48fb1)
        start = self.page * LEVELS_PER_PAGE
        end = start + LEVELS_PER_PAGE

        for i in range(start, end):
            if i >= len(self.levels):
                break
            level = self.levels[i]
            role_text = f"<@&{level.get('role')}>" if level.get("role") else "chưa đặt"
            days_text = str(level.get("days")) if level.get("days") is not None else "chưa đặt"
            embed.add_field(name=f"Level {i+1}", value=f"Role: {role_text}\nDays: {days_text}", inline=False)

        embed.set_footer(text=f"Page {self.page+1}/{self.max_page+1}")
        return embed

    # =========================
    # COMPONENTS
    # =========================
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

    async def refresh(self, interaction):
        self.max_page = max(0, (len(self.levels)-1)//LEVELS_PER_PAGE)
        if self.page > self.max_page:
            self.page = self.max_page
        self.update_components()
        embed = self.build_embed()
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    # =========================
    # PAGE NAVIGATION
    # =========================
    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
        await self.refresh(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        if self.page < self.max_page:
            self.page += 1
        await self.refresh(interaction)

    @discord.ui.button(label="+", style=discord.ButtonStyle.success)
    async def add_page(self, interaction, button):
        if self.max_page + 1 >= MAX_PAGES:
            await interaction.response.send_message("Đã đạt giới hạn 100 level.", ephemeral=True)
            return
        for _ in range(LEVELS_PER_PAGE):
            self.levels.append({"role": None, "days": None})
        self.page = self.max_page + 1
        await self.refresh(interaction)

    # =========================
    # EDIT
    # =========================
    @discord.ui.button(label="Edit Role", style=discord.ButtonStyle.secondary)
    async def edit_role(self, interaction, button):
        index = self.selected_level

        class Modal(discord.ui.Modal, title="Set Role"):
            role = discord.ui.TextInput(label="Role ID hoặc mention")
            async def on_submit(modal_self, i):
                val = modal_self.role.value.strip()
                if val.startswith("<@&"):
                    val = val[3:-1]
                if not val.isdigit():
                    await i.response.send_message("Role không hợp lệ", ephemeral=True)
                    return
                self.levels[index]["role"] = int(val)
                await self.refresh(i)

        await interaction.response.send_modal(Modal())

    @discord.ui.button(label="Edit Days", style=discord.ButtonStyle.secondary)
    async def edit_days(self, interaction, button):
        index = self.selected_level
        if index == 0:
            await interaction.response.send_message("Level 1 luôn = 0 ngày", ephemeral=True)
            return

        class Modal(discord.ui.Modal, title="Set Days"):
            days = discord.ui.TextInput(label="Days")
            async def on_submit(modal_self, i):
                if not modal_self.days.value.isdigit():
                    await i.response.send_message("Days không hợp lệ", ephemeral=True)
                    return
                self.levels[index]["days"] = int(modal_self.days.value)
                await self.refresh(i)

        await interaction.response.send_modal(Modal())

    # =========================
    # MOVE
    # =========================
    @discord.ui.button(label="↑", style=discord.ButtonStyle.secondary)
    async def move_up(self, interaction, button):
        i = self.selected_level
        if i <= 1:
            await interaction.response.send_message("Không thể di chuyển Level 1", ephemeral=True)
            return
        self.levels[i], self.levels[i-1] = self.levels[i-1], self.levels[i]
        self.selected_level -= 1
        await self.refresh(interaction)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.secondary)
    async def move_down(self, interaction, button):
        i = self.selected_level
        if i >= len(self.levels) - 1:
            return
        self.levels[i], self.levels[i+1] = self.levels[i+1], self.levels[i]
        self.selected_level += 1
        await self.refresh(interaction)

    # =========================
    # DELETE
    # =========================
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_level(self, interaction, button):
        if self.selected_level == 0:
            await interaction.response.send_message("Không thể xoá Level 1", ephemeral=True)
            return
        self.levels.pop(self.selected_level)
        if self.selected_level >= len(self.levels):
            self.selected_level -= 1
        await self.refresh(interaction)

    # =========================
    # SAVE
    # =========================
    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary)
    async def save_btn(self, interaction, button):
        prev_days = -1
        for i, lvl in enumerate(self.levels):
            role = lvl.get("role")
            days = lvl.get("days")
            if role is None or days is None:
                await interaction.response.send_message("Level thiếu dữ liệu", ephemeral=True)
                return
            if i == 0 and days != 0:
                await interaction.response.send_message("Level 1 phải = 0", ephemeral=True)
                return
            if days <= prev_days:
                await interaction.response.send_message("Days phải tăng dần", ephemeral=True)
                return
            prev_days = days

        interaction.client.dispatch("booster_level_save", interaction.guild.id, self.levels)
        await interaction.response.send_message("Đã lưu", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction, button):
        await interaction.response.send_message("Đã huỷ", ephemeral=True)
        self.stop()

# =========================
# HELPER FUNCTION
# =========================
async def open_booster_level_ui(bot, ctx, guild_id: int, levels: list):
    # Xoá UI cũ nếu tồn tại
    for msg in getattr(bot, "_booster_ui_messages", []):
        try:
            await msg.delete()
        except:
            pass
    bot._booster_ui_messages = []

    view = BoosterLevelView(guild_id, levels)
    message = await ctx.send(embed=view.build_embed(), view=view)
    view.message = message
    bot._booster_ui_messages.append(message)
