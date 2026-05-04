import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re # Tiêm thêm để lọc ký tự

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
            "staff_role_ids": [], # Cập nhật sang danh sách
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
    # LỆNH 1: SETUP THÔNG MINH (ĐÃ CẬP NHẬT)
    # =========================
    @app_commands.command(name="setup", description="Cấu hình Ticket (Gõ nhiều role cách nhau bằng dấu /)")
    @app_commands.describe(
        category_id="ID danh mục hoặc Tag danh mục",
        staff_roles="ID role hoặc Tag các role nhân viên (Ví dụ: @Role1 / @Role2)",
        log_channel_id="ID kênh hoặc Tag kênh gửi transcript"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, staff_roles: str, log_channel_id: str):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        
        # --- BẮT ĐẦU MẠCH CẬP NHẬT (LỌC & TÁCH) ---
        def sanitize(text): return re.sub(r'\D', '', text) # Hàm gọt sạch ký tự lạ
        
        # 1. Gọt sạch ID Kênh và Danh mục
        clean_cat_id = sanitize(category_id)
        clean_log_id = sanitize(log_channel_id)
        
        # 2. Tách và gọt danh sách Role Staff
        # Tách theo: dấu gạch chéo (/), dấu phẩy (,) hoặc khoảng trắng
        raw_parts = re.split(r'[/,\s]+', staff_roles)
        clean_staff_ids = [sanitize(p) for p in raw_parts if sanitize(p)]
        # --- KẾT THÚC MẠCH CẬP NHẬT ---

        try:
            cat = guild.get_channel(int(clean_cat_id)) if clean_cat_id else None
            log = guild.get_channel(int(clean_log_id)) if clean_log_id else None
            
            # Kiểm tra xem có ít nhất 1 role hợp lệ không
            valid_roles = []
            for r_id in clean_staff_ids:
                role = guild.get_role(int(r_id))
                if role: valid_roles.append(role)
            
            if not cat or not log or not valid_roles:
                return await interaction.followup.send("❌ Yiyi không tìm thấy Kênh hoặc Role nào hợp lệ. Sếp kiểm tra lại ID/Tag nhé!")
        except (ValueError, TypeError):
            return await interaction.followup.send("❌ Dữ liệu nhập vào không đúng định dạng số ID.")

        config = self._get_config(guild.id)
        config.update({
            "category_id": str(clean_cat_id),
            "staff_role_ids": [str(r.id) for r in valid_roles], # Lưu mảng ID
            "log_channel_id": str(clean_log_id)
        })
        
        self._save_config(guild.id, config)
        await force_save(FILE_KEY)
        
        role_mentions = ", ".join([r.mention for r in valid_roles])
        await interaction.followup.send(
            f"✅ **Ticket Setup:** Đã lưu cấu hình!\n"
            f"• Danh mục: {cat.name}\n"
            f"• Staff Roles ({len(valid_roles)}): {role_mentions}\n"
            f"• Log Channel: {log.name}"
        )

    # =========================
    # LỆNH 2: CẤY NÚT MỞ TICKET (GIỮ NGUYÊN)
    # =========================
    @app_commands.command(name="apply", description="Gắn nút mở ticket vào Embed thiết kế")
    @app_commands.describe(embed_name="Tên embed muốn gắn nút")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        config = self._get_config(guild_id)

        # Cập nhật check: Kiểm tra danh sách role thay vì 1 role
        if not config.get("category_id") or not config.get("staff_role_ids"):
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

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "ticket"), None)
        if existing: 
            p_cmd.remove_command("ticket")
        
        p_cmd.add_command(TicketGroup())
        print("[LOAD] Success: commands.ticket.ticket_group", flush=True)
