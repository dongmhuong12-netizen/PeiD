import discord
from core.booster_storage import save_levels
from core.boost_utils import (
    validate_levels, 
    move_level_up, 
    move_level_down, 
    format_level_status,
    cleanup_deleted_roles
)
from core.boost_modal import RoleInputModal, DaysInputModal
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

LEVELS_PER_PAGE = 10
MAX_LEVELS = 100

class LevelSelect(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = []
        
        start = parent_view.page * LEVELS_PER_PAGE
        end = min(start + LEVELS_PER_PAGE, len(parent_view.levels))

        for i in range(start, end):
            lvl = parent_view.levels[i]
            role_id = lvl.get("role")
            days = lvl.get("days", 0)
            
            role_label = f"id: {role_id}" if role_id else "chưa thiết lập"
            
            options.append(
                discord.SelectOption(
                    label=f"level {i + 1}",
                    description=f"days: {days} | {role_label}",
                    value=str(i),
                    default=(i == parent_view.selected_level)
                )
            )

        super().__init__(placeholder="chọn level để chỉnh sửa...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_level = int(self.values[0])
        await self.parent_view.refresh(interaction)

class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list, booster_role: int):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.booster_role = booster_role
        self.page = 0
        self.selected_level = 0
        self.message = None
        
        self.levels = [lvl.copy() for lvl in levels] if levels else []
        
        if not self.levels:
            self.levels.append({"role": booster_role, "days": 0})
        else:
            self.levels[0]["role"] = booster_role
            self.levels[0]["days"] = 0
            
        self._fill_slots()
        self.update_components()

    def _fill_slots(self):
        required = min((self.page + 1) * LEVELS_PER_PAGE, MAX_LEVELS)
        while len(self.levels) < required:
            self.levels.append({"role": None, "days": None})

    def get_total_pages(self):
        return max(1, (len(self.levels) - 1) // LEVELS_PER_PAGE + 1)

    def build_embed(self):
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cấu hình booster levels",
            description=f"thiết lập các mốc quà tặng cho người ủng hộ server.\n**đang chọn:** `level {self.selected_level + 1}`",
            color=0xf8bbd0
        )
        
        start = self.page * LEVELS_PER_PAGE
        end = min(start + LEVELS_PER_PAGE, len(self.levels))

        for i in range(start, end):
            status = format_level_status(i, self.levels[i], self.message.guild if self.message else None)
            name = f"🔹 level {i+1}" if i == self.selected_level else f"level {i+1}"
            embed.add_field(name=name, value=status, inline=True)

        embed.set_footer(text=f"trang {self.page + 1}/{self.get_total_pages()} • tối đa {MAX_LEVELS} levels")
        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(LevelSelect(self))
        
        self.add_item(self.prev_page)
        self.add_item(discord.ui.Button(label=f"{self.page + 1}/{self.get_total_pages()}", disabled=True, row=1))
        self.add_item(self.add_page)
        self.add_item(self.next_page)
        
        self.add_item(self.edit_role_btn)
        self.add_item(self.edit_days_btn)
        self.add_item(self.move_up_btn)
        self.add_item(self.move_down_btn)
        self.add_item(self.delete_btn)
        
        self.add_item(self.save_btn)
        self.add_item(self.cancel_btn)

    async def refresh(self, interaction: discord.Interaction = None):
        self._fill_slots()
        self.update_components()
        embed = self.build_embed()
        
        if interaction and not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.gray, row=1)
    async def prev_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
            self.selected_level = self.page * LEVELS_PER_PAGE
            await self.refresh(interaction)
        else:
            await interaction.response.send_message(f"{Emojis.HOICHAM} đây là trang đầu tiên rồi cậu nhé", ephemeral=True)

    @discord.ui.button(label="+ page", style=discord.ButtonStyle.green, row=1)
    async def add_page(self, interaction, button):
        if len(self.levels) >= MAX_LEVELS:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} aree... đã đạt giới hạn tối đa `{MAX_LEVELS}` level rồi", ephemeral=True)

        start_idx = self.page * LEVELS_PER_PAGE
        end_idx = start_idx + LEVELS_PER_PAGE
        current_page_levels = self.levels[start_idx:end_idx]

        is_page_complete = all(
            lvl.get("role") is not None and lvl.get("days") is not None 
            for lvl in current_page_levels
        )

        if not is_page_complete:
            return await interaction.response.send_message(
                f"{Emojis.HOICHAM} cậu cần hoàn tất thiết lập `role` và `days` cho toàn bộ 10 level của `trang {self.page + 1}` trước khi tạo trang mới",
                ephemeral=True
            )

        self.page += 1
        self.selected_level = self.page * LEVELS_PER_PAGE
        await self.refresh(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.gray, row=1)
    async def next_page(self, interaction, button):
        if self.page < self.get_total_pages() - 1:
            self.page += 1
            self.selected_level = self.page * LEVELS_PER_PAGE
            await self.refresh(interaction)
        else:
            await interaction.response.send_message(f"{Emojis.HOICHAM} đây là trang cuối cùng rồi", ephemeral=True)

    @discord.ui.button(label="sửa role", style=discord.ButtonStyle.blurple, row=2)
    async def edit_role_btn(self, interaction, button):
        current = self.levels[self.selected_level].get("role")
        async def callback(it, role_id):
            self.levels[self.selected_level]["role"] = role_id
            await it.response.defer()
            await self.refresh()
        await interaction.response.send_modal(RoleInputModal(current, callback))

    @discord.ui.button(label="sửa ngày", style=discord.ButtonStyle.blurple, row=2)
    async def edit_days_btn(self, interaction, button):
        if self.selected_level == 0:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} `level 1` mặc định là 0 ngày và không thể chỉnh sửa đâu", ephemeral=True)
        current = self.levels[self.selected_level].get("days")
        async def callback(it, days):
            self.levels[self.selected_level]["days"] = days
            await it.response.defer()
            await self.refresh()
        await interaction.response.send_modal(DaysInputModal(current, callback))

    @discord.ui.button(label="↑", style=discord.ButtonStyle.gray, row=3)
    async def move_up_btn(self, interaction, button):
        self.levels = move_level_up(self.levels, self.selected_level)
        if self.selected_level > 1: self.selected_level -= 1
        await self.refresh(interaction)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.gray, row=3)
    async def move_down_btn(self, interaction, button):
        self.levels = move_level_down(self.levels, self.selected_level)
        if self.selected_level < len(self.levels) - 1: self.selected_level += 1
        await self.refresh(interaction)

    @discord.ui.button(label="xóa level", style=discord.ButtonStyle.red, row=3)
    async def delete_btn(self, interaction, button):
        if self.selected_level == 0:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} yiyi không thể xóa `level 1` mặc định được", ephemeral=True)
        self.levels.pop(self.selected_level)
        self.selected_level = max(0, self.selected_level - 1)
        await self.refresh(interaction)

    @discord.ui.button(label="lưu cấu hình", style=discord.ButtonStyle.success, row=4)
    async def save_btn(self, interaction, button):
        cleaned = [lvl for lvl in self.levels if lvl.get("role") is not None and lvl.get("days") is not None]
        success, error_msg = validate_levels(cleaned, self.booster_role)
        if not success:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} lưu thất bại: `{error_msg}`", ephemeral=True)
        
        await save_levels(interaction.guild.id, cleaned)
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send(f"{Emojis.MATTRANG} đã lưu thành công `{len(cleaned)}` levels!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="hủy bỏ", style=discord.ButtonStyle.secondary, row=4)
    async def cancel_btn(self, interaction, button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send("đã hủy các thay đổi", ephemeral=True)
        self.stop()
