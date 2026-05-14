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
        super().__init__(name="ticket", description="Hệ thống hỗ trợ và quản lý Ticket")

    def _sanitize(self, text): 
        if not text: return ""
        return re.sub(r'\D', '', text)

    # =========================
    # LỆNH 1: SETUP (Tối ưu thứ tự nhập liệu)
    # =========================
    @app_commands.command(name="setup", description="Cấu hình hệ thống Ticket")
    @app_commands.describe(
        category_id="1. ID danh mục hoặc Tag danh mục",
        log_channel_id="2. ID kênh hoặc Tag kênh gửi transcript",
        staff_roles="3. ID/Tag các role nhân viên (Cách nhau bởi dấu phẩy/khoảng trắng)"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, log_channel_id: str, staff_roles: str):
        """
        Đã đảo thứ tự: Danh mục -> Log Channel -> Staff Roles (để nhập nhiều ID ở cuối).
        """
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        # Làm sạch ID
        clean_cat_id = self._sanitize(category_id)
        clean_log_id = self._sanitize(log_channel_id)
        
        # Tách danh sách role staff
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
            
            if not cat or not log or not valid_roles_obj:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                    description=f"**yiyi** không tìm thấy kênh hoặc role hợp lệ. cậu hãy kiểm tra lại ID nhé.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed_err)
        except (ValueError, TypeError):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm...? định dạng lỗi",
                description="dữ liệu ID không đúng định dạng số, xin hãy kiểm tra lại.",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_err)

        # [KẾT NỐI MẠCH] Đồng bộ cấu hình lên MongoDB
        config_data = {
            "category_id": clean_cat_id,
            "staff_roles": valid_roles_ids,
            "log_channel_id": clean_log_id
        }
        
        success = await update_ticket_config(interaction.guild.id, config_data)
        
        if success:
            role_mentions = "\n".join([f"• {r.mention}" for r in valid_roles_obj])
            embed_res = discord.Embed(
                title=f"{Emojis.MATTRANG} cập nhật cấu hình Ticket thành công",
                description=(
                    f"• danh mục: `{cat.name}`\n"
                    f"• kênh trả nội dung: `{log.name}`\n"
                    f"• staff role (`{len(valid_roles_obj)}`):\n{role_mentions}"
                ),
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_res)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Không thể lưu cấu hình vào Cloud Atlas.")

    # =========================
    # LỆNH 2: APPLY (Đã fix lỗi hiển thị & Đồng bộ Dashboard)
    # =========================
    @app_commands.command(name="apply", description="Liên kết Ticket vào Embed")
    @app_commands.describe(embed_name="Tên embed muốn gắn nút Ticket")
    async def apply(self, interaction: discord.Interaction, embed_name: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        config = await get_ticket_config(guild_id)
        if not config or not config.get("category_id"):
            embed_no_config = discord.Embed(
                title=f"{Emojis.HOICHAM} chưa có cấu hình.",
                description="cậu cần thực hiện lệnh `/p ticket setup` trước nhé.",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_no_config)

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

        # Cập nhật nút bấm vào Embed
        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:ticket:open", button_data=btn_data)
        
        if not updated:
            success = await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")
            if not success:
                embed_full = discord.Embed(
                    title=f"{Emojis.HOICHAM} không thể liên kết.",
                    description="embed đã đầy nút bấm, không thể thêm Ticket.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed_full)

        # [CHỐT HẠ] Cập nhật tên Embed vào Config để Dashboard (yiyi setting) lấy được data
        # Tuyệt đối lưu dạng String để Dashboard hiển thị sạch sẽ
        await update_ticket_config(guild_id, {"embed_name": str(embed_name)})

        # [FIX LỖI IMAGE_23] Đã thêm tường minh tham số embed=
        embed_ok = discord.Embed(
            title=f"{Emojis.MATTRANG} liên kết Ticket vào embed `{embed_name}` thành công.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_ok)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "ticket"), None)
        if existing: 
            p_cmd.remove_command("ticket")
        p_cmd.add_command(TicketGroup())
        print("[LOAD] Success: commands.ticket.ticket_group (Industrial Order Optimized)", flush=True)
