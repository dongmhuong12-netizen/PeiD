import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.embed_storage import load_embed, atomic_update_button
from core.cache_manager import get_raw, mark_dirty, update, save as force_save

FILE_KEY = "ticket_configs"

class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="Hệ thống hỗ trợ và quản lý Ticket chuyên nghiệp")

    def _get_config(self, guild_id):
        """Truy xuất cấu hình ticket từ bộ nhớ tạm"""
        db = get_raw(FILE_KEY)
        if not isinstance(db, dict):
            db = {}
            update(FILE_KEY, db)
        return db.get(str(guild_id), {
            "category_id": None,
            "staff_role_id": None,
            "log_channel_id": None,
            "ticket_count": 0
        })

    def _save_config(self, guild_id, config):
        """Ghi nhận cấu hình mới vào database"""
        db = get_raw(FILE_KEY)
        db[str(guild_id)] = config
        update(FILE_KEY, db)
        mark_dirty(FILE_KEY)

    # =========================
    # LỆNH 1: SETUP THỦ CÔNG QUA ID
    # =========================
    @app_commands.command(name="setup", description="Cấu hình ID hệ thống ticket (Manual Mode)")
    @app_commands.describe(
        category_id="ID danh mục chứa các kênh ticket",
        staff_role_id="ID role của nhân viên hỗ trợ",
        log_channel_id="ID kênh gửi bản lưu (transcript) sau khi đóng"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, staff_role_id: str, log_channel_id: str):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        try:
            cat = guild.get_channel(int(category_id))
            role = guild.get_role(int(staff_role_id))
            log = guild.get_channel(int(log_channel_id))
            
            if not all([cat, role, log]):
                return await interaction.followup.send("❌ Một hoặc nhiều ID không hợp lệ trong server này. Sếp kiểm tra lại nhé!")
        except ValueError:
            return await interaction.followup.send("❌ Vui lòng chỉ nhập số ID, không nhập ký tự lạ.")

        config = self._get_config(guild.id)
        config.update({
            "category_id": str(category_id),
            "staff_role_id": str(staff_role_id),
            "log_channel_id": str(log_channel_id)
        })
        
        self._save_config(guild.id, config)
        await force_save(FILE_KEY)
        
        await interaction.followup.send(
            f"✅ **Ticket Setup:** Đã lưu cấu hình!\n"
            f"• Danh mục: {cat.name}\n"
            f"• Staff Role: {role.name}\n"
            f"• Log Channel: {log.name}"
        )

    # =========================
    # LỆNH 2: CẤY NÚT MỞ TICKET
    # =========================
    @app_commands.command(name="apply", description="Gắn nút mở ticket vào Embed thiết kế")
    @app_commands.describe(embed_name="Tên embed muốn gắn nút")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        config = self._get_config(guild_id)

        if not config["category_id"] or not config["staff_role_id"]:
            return await interaction.followup.send("❌ Hệ thống chưa được setup! Dùng `/p ticket setup` trước sếp ơi.")

        btn_data = {
            "type": "button",
            "style": "primary",
            "label": "Mở yêu cầu hỗ trợ",
            "emoji": "🎫",
            "custom_id": "yiyi:ticket:open",
            "system": "ticket"
        }

        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:ticket:open", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                return await interaction.followup.send("❌ Không thể gắn nút. Embed có thể đã đầy.")

        await interaction.followup.send(f"✅ Đã cấy mạch Ticket vào embed `{embed_name}` thành công!")

# =========================
# INJECTION (Ổ CẮM CHUẨN)
# =========================
async def setup(bot: commands.Bot): # Đổi từ setup_ext thành setup
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "ticket"), None)
        if existing: 
            p_cmd.remove_command("ticket")
        
        p_cmd.add_command(TicketGroup())
        print("[LOAD] Success: commands.ticket.ticket_group", flush=True)
