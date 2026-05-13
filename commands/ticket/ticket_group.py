import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re

# Nạp công cụ Storage và Trí nhớ Ticket mới (Industrial Standard)
from core.embed_storage import load_embed, atomic_update_button
from core.ticket_storage import update_ticket_config, get_ticket_config
from utils.emojis import Emojis

class TicketGroup(app_commands.Group):
    def __init__(self):
        # [MỤC 1] Giữ nguyên mô tả đã gọt
        super().__init__(name="ticket", description="Hệ thống hỗ trợ và quản lý Ticket")

    def _sanitize(self, text): 
        return re.sub(r'\D', '', text)

    # =========================
    # LỆNH 1: SETUP (Đã hàn mạch MongoDB)
    # =========================
    @app_commands.command(name="setup", description="Cấu hình Ticket")
    @app_commands.describe(
        category_id="ID danh mục hoặc Tag danh mục",
        staff_roles="ID role hoặc Tag các role nhân viên",
        log_channel_id="ID kênh hoặc Tag kênh gửi transcript"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, staff_roles: str, log_channel_id: str):
        # QUY TẮC 3S: Defer ngay lập tức để giữ mạch kết nối (Industrial Standard)
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        clean_cat_id = self._sanitize(category_id)
        clean_log_id = self._sanitize(log_channel_id)
        
        raw_parts = re.split(r'[/,\s]+', staff_roles)
        clean_staff_ids = [self._sanitize(p) for p in raw_parts if self._sanitize(p)]

        try:
            cat = guild.get_channel(int(clean_cat_id)) if clean_cat_id else None
            log = guild.get_channel(int(clean_log_id)) if clean_log_id else None
            
            valid_roles_ids = []
            valid_roles_obj = []
            for r_id in clean_staff_ids:
                role = guild.get_role(int(r_id))
                if role: 
                    valid_roles_ids.append(r_id)
                    valid_roles_obj.append(role)
            
            # [MỤC 4] Kiểm tra tính hợp lệ của nội dung
            if not cat or not log or not valid_roles_obj:
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

        # [KẾT NỐI MẠCH] Đồng bộ cấu hình Ticket lên Cloud Atlas
        config_data = {
            "category_id": clean_cat_id,
            "staff_roles": valid_roles_ids,
            "log_channel_id": clean_log_id
        }
        
        # Lưu vào MongoDB thông qua Storage đã bóc tách
        success = await update_ticket_config(interaction.guild.id, config_data)
        
        if success:
            # [MỤC 6] Setup thành công với văn phong của Nguyệt
            role_mentions = "\n".join([f"• {r.mention}" for r in valid_roles_obj])
            embed_res = discord.Embed(
                title=f"{Emojis.MATTRANG} cập nhật cấu hình Ticket thành công",
                description=(
                    f"• danh mục: `{cat.name}`\n"
                    f"• staff role (`{len(valid_roles_obj)}`):\n{role_mentions}\n"
                    f"• kênh trả nội dung: `{log.name}`"
                ),
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_res)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Không thể kết nối với Cloud Atlas để lưu cấu hình.")

    # =========================
    # LỆNH 2: APPLY (Liên kết Ticket)
    # =========================
    @app_commands.command(name="apply", description="Liên kết Ticket vào Embed")
    @app_commands.describe(embed_name="Tên embed gắn đơn")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        # [GIA CỐ] Defer sớm để bảo vệ interaction
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        # [KẾT NỐI MẠCH] Kiểm tra cấu hình Ticket
        config = await get_ticket_config(guild_id)
        if not config or not config.get("category_id"):
            embed_no_config = discord.Embed(
                title=f"{Emojis.HOICHAM} chưa có cấu hình.",
                description="cậu cần thực hiện lệnh `/p ticket setup` trước khi liên kết vào embed nhé.",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_no_config)

        # Kiểm tra sự tồn tại của Embed
        if not await load_embed(guild_id, embed_name):
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{embed_name}`.")

        btn_data = {
            "type": "button",
            "style": "primary",
            "label": "Ticket",
            "emoji": f"{Emojis.MATTRANG}", 
            "custom_id": "yiyi:ticket:open",
            "system": "ticket"
        }

        # [GIA CỐ] Cập nhật nút bấm
        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:ticket:open", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                embed_full = discord.Embed(
                    title=f"{Emojis.HOICHAM} không thể liên kết.",
                    description="embed cậu muốn liên kết có thể đã full slot cấu hình, hãy thử chọn embed khác hoặc tạo mới nhé.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed_full)

        # [CHỐT HẠ] Cập nhật tên Embed vào Ticket Config để Dashboard (yiyi setting) lấy được data
        # CHỈ LƯU TÊN (STRING), tuyệt đối không lưu Object để tránh lỗi <discord.embeds.Embed...>
        await update_ticket_config(guild_id, {"embed_name": str(embed_name)})

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
        print("[LOAD] Success: commands.ticket.ticket_group (Industrial Fix Applied)", flush=True)
