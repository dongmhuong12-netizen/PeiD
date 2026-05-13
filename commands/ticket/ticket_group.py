import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re

from core.embed_storage import load_embed, atomic_update_button
# [TRÍ NHỚ ĐÃ BÓC TÁCH] Gỡ bỏ các import liên quan đến cache manager cục bộ
from utils.emojis import Emojis

class TicketGroup(app_commands.Group):
    def __init__(self):
        # [MỤC 1] Bỏ chữ "chuyên nghiệp"
        super().__init__(name="ticket", description="Hệ thống hỗ trợ và quản lý Ticket")

    # =========================
    # LỆNH 1: SETUP (Đã gọt văn phong & đóng khung code)
    # =========================
    @app_commands.command(name="setup", description="Cấu hình Ticket") # [MỤC 2]
    @app_commands.describe(
        category_id="ID danh mục hoặc Tag danh mục",
        staff_roles="ID role hoặc Tag các role nhân viên", # [MỤC 3]
        log_channel_id="ID kênh hoặc Tag kênh gửi transcript"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, staff_roles: str, log_channel_id: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        def sanitize(text): return re.sub(r'\D', '', text)
        clean_cat_id = sanitize(category_id)
        clean_log_id = sanitize(log_channel_id)
        
        raw_parts = re.split(r'[/,\s]+', staff_roles)
        clean_staff_ids = [sanitize(p) for p in raw_parts if sanitize(p)]

        try:
            cat = guild.get_channel(int(clean_cat_id)) if clean_cat_id else None
            log = guild.get_channel(int(clean_log_id)) if clean_log_id else None
            
            valid_roles = []
            for r_id in clean_staff_ids:
                role = guild.get_role(int(r_id))
                if role: valid_roles.append(role)
            
            # [MỤC 4] Lỗi không tìm thấy nội dung
            if not cat or not log or not valid_roles:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} hmm...? có lỗi gì đó ở đây",
                    description=f"**yiyi** không tìm thấy kênh hoặc role có nội dung tương tự, cậu hãy thử nhập lại lần nữa nhé.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed_err)
        except (ValueError, TypeError):
            # [MỤC 5] Lỗi định dạng ID
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm...? có lỗi gì đó ở đây",
                description="dữ liệu nhập vào không đúng định dạng số id, xin hãy nhập lại.",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_err)

        # [TRÍ NHỚ ĐÃ BÓC TÁCH] 
        # Cậu sẽ thay thế logic lấy/cập nhật config vào MongoDB tại đây.
        # Logic chuẩn hóa dữ liệu cat/log/roles vẫn được giữ nguyên 100%.
        
        # [MỤC 6] Setup thành công
        role_mentions = "\n".join([f"• {r.mention}" for r in valid_roles])
        embed_res = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật cấu hình Ticket thành công",
            description=(
                f"• danh mục: `{cat.name}`\n"
                f"• staff role (`{len(valid_roles)}`):\n{role_mentions}\n"
                f"• kênh trả nội dung: `{log.name}`"
            ),
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_res)

    # =========================
    # LỆNH 2: APPLY (Liên kết Ticket)
    # =========================
    @app_commands.command(name="apply", description="Liên kết Ticket vào Embed") # [MỤC 7]
    @app_commands.describe(embed_name="Tên embed gắn đơn")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # [TRÍ NHỚ ĐÃ BÓC TÁCH]
        # Xóa bỏ các lệnh gọi _get_config. 
        # Cần kiểm tra config từ MongoDB tại đây trước khi thực hiện cấy nút bấm.

        btn_data = {
            "type": "button",
            "style": "primary",
            "label": "Ticket", # Nhãn gọn theo ý sếp
            "emoji": f"{Emojis.MATTRANG}", # [MỤC 9] Dùng emoji sếp dặn
            "custom_id": "yiyi:ticket:open",
            "system": "ticket"
        }

        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:ticket:open", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                # [MỤC 10] Lỗi full slot
                embed_full = discord.Embed(
                    title=f"{Emojis.HOICHAM} không thể liên kết.",
                    description="embed cậu muốn liên kết có thể đã full slot cấu hình, hãy thử chọn embed khác hoặc tạo mới nhé.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed_full)

        # [MỤC 11] Apply thành công
        embed_ok = discord.Embed(
            title=f"{Emojis.MATTRANG} liên kết Ticket vào embed `{embed_name}` thành công.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed_ok)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "ticket"), None)
        if existing: 
            p_cmd.remove_command("ticket")
        p_cmd.add_command(TicketGroup())
        print("[LOAD] Success: commands.ticket.ticket_group", flush=True)
