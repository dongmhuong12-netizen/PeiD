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
            
            # Hiển thị ngắn gọn trong menu
            role_label = f"ID: {role_id}" if role_id else "Chưa thiết lập"
            
            options.append(
                discord.SelectOption(
                    label=f"Level {i + 1}",
                    description=f"Days: {days} | {role_label}",
                    value=str(i),
                    default=(i == parent_view.selected_level)
                )
            )

        super().__init__(placeholder="Chọn Level để chỉnh sửa...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_level = int(self.values[0])
        await self.parent_view.refresh(interaction)

class BoosterLevelView(discord.ui.View):
    def __init__(self, guild_id: int, levels: list, booster_role: int):
        super().__init__(timeout=600) # 10 phút tự dọn dẹp RAM
        self.guild_id = guild_id
        self.booster_role = booster_role
        self.page = 0
        self.selected_level = 0
        self.message = None
        
        # Clone dữ liệu để chỉnh sửa tạm thời (Draft mode)
        self.levels = [lvl.copy() for lvl in levels] if levels else []
        
        # Luôn đảm bảo Level 1 là Booster Role mặc định (Quy tắc 2)
        if not self.levels:
            self.levels.append({"role": booster_role, "days": 0})
        else:
            self.levels[0]["role"] = booster_role
            self.levels[0]["days"] = 0
            
        self._fill_slots()
        self.update_components()

    def _fill_slots(self):
        """Đảm bảo luôn có đủ slot cho trang hiện tại"""
        required = min((self.page + 1) * LEVELS_PER_PAGE, MAX_LEVELS)
        while len(self.levels) < required:
            self.levels.append({"role": None, "days": None})

    def get_total_pages(self):
        return max(1, (len(self.levels) - 1) // LEVELS_PER_PAGE + 1)

    def build_embed(self):
        embed = discord.Embed(
            title="💎 Cấu hình Booster Levels",
            description=f"Đang chỉnh sửa hệ thống Level cho Server.\n**Level được chọn:** `Level {self.selected_level + 1}`",
            color=0xf48fb1
        )
        
        start = self.page * LEVELS_PER_PAGE
        end = min(start + LEVELS_PER_PAGE, len(self.levels))

        for i in range(start, end):
            # Dùng hàm format chuẩn từ utils
            status = format_level_status(i, self.levels[i], self.message.guild if self.message else None)
            
            # Highlight level đang được chọn
            name = f"🔹 Level {i+1}" if i == self.selected_level else f"Level {i+1}"
            embed.add_field(name=name, value=status, inline=True)

        embed.set_footer(text=f"Trang {self.page + 1}/{self.get_total_pages()} • Tối đa {MAX_LEVELS} Levels")
        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(LevelSelect(self))
        
        # Navigation Row (Row 1)
        self.add_item(self.prev_page)
        self.add_item(discord.ui.Button(label=f"{self.page + 1}/{self.get_total_pages()}", disabled=True, row=1))
        self.add_item(self.add_page)
        self.add_item(self.next_page)
        
        # Editor Row (Row 2 & 3)
        self.add_item(self.edit_role_btn)
        self.add_item(self.edit_days_btn)
        self.add_item(self.move_up_btn)
        self.add_item(self.move_down_btn)
        self.add_item(self.delete_btn)
        
        # Action Row (Row 4)
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

    # --- HÀNH ĐỘNG ---
    
    @discord.ui.button(label="<", style=discord.ButtonStyle.gray, row=1)
    async def prev_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
            self.selected_level = self.page * LEVELS_PER_PAGE
            await self.refresh(interaction)
        else:
            await interaction.response.send_message("Đây là trang đầu tiên!", ephemeral=True)

    @discord.ui.button(label="+ Page", style=discord.ButtonStyle.green, row=1)
    async def add_page(self, interaction, button):
        if len(self.levels) < MAX_LEVELS:
            self.page = self.get_total_pages()
            self._fill_slots()
            self.selected_level = self.page * LEVELS_PER_PAGE
            await self.refresh(interaction)
        else:
            await interaction.response.send_message("Đã đạt giới hạn 100 Level!", ephemeral=True)

    @discord.ui.button(label=">", style=discord.ButtonStyle.gray, row=1)
    async def next_page(self, interaction, button):
        if self.page < self.get_total_pages() - 1:
            self.page += 1
            self.selected_level = self.page * LEVELS_PER_PAGE
            await self.refresh(interaction)
        else:
            await interaction.response.send_message("Đây là trang cuối cùng!", ephemeral=True)

    @discord.ui.button(label="Sửa Role", style=discord.ButtonStyle.blurple, row=2)
    async def edit_role_btn(self, interaction, button):
        current = self.levels[self.selected_level].get("role")
        
        async def callback(it, role_id):
            self.levels[self.selected_level]["role"] = role_id
            await it.response.defer()
            await self.refresh()
            
        await interaction.response.send_modal(RoleInputModal(current, callback))

    @discord.ui.button(label="Sửa Ngày", style=discord.ButtonStyle.blurple, row=2)
    async def edit_days_btn(self, interaction, button):
        if self.selected_level == 0:
            return await interaction.response.send_message("Level 1 mặc định là 0 ngày và không thể chỉnh sửa.", ephemeral=True)
            
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

    @discord.ui.button(label="Xóa Level", style=discord.ButtonStyle.red, row=3)
    async def delete_btn(self, interaction, button):
        if self.selected_level == 0:
            return await interaction.response.send_message("Không thể xóa Level 1 mặc định.", ephemeral=True)
        
        self.levels.pop(self.selected_level)
        self.selected_level = max(0, self.selected_level - 1)
        await self.refresh(interaction)

    @discord.ui.button(label="LƯU CẤU HÌNH", style=discord.ButtonStyle.success, row=4)
    async def save_btn(self, interaction, button):
        # 1. Loại bỏ các slot trống chưa thiết lập
        cleaned = [lvl for lvl in self.levels if lvl.get("role") is not None and lvl.get("days") is not None]
        
        # 2. Chạy Validation theo kế hoạch 43 mục
        success, error_msg = validate_levels(cleaned, self.booster_role)
        
        if not success:
            return await interaction.response.send_message(f"❌ **Lưu thất bại:** {error_msg}", ephemeral=True)
            
        # 3. Ghi xuống đĩa thông qua Storage (Atomic)
        await save_levels(interaction.guild.id, cleaned)
        await interaction.response.send_message(f"✅ Đã lưu thành công **{len(cleaned)}** Levels!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="HỦY BỎ", style=discord.ButtonStyle.secondary, row=4)
    async def cancel_btn(self, interaction, button):
        await interaction.response.send_message("Đã hủy các thay đổi.", ephemeral=True)
        self.stop()
