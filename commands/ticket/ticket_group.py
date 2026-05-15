import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re

# Nạp công cụ Storage và Trí nhớ Ticket mới (Industrial Standard)
from core.embed_storage import load_embed, atomic_update_button, get_all_embed_names
from core.ticket_storage import update_ticket_config, get_ticket_config
from utils.emojis import Emojis

# =============================
# HELPERS (Bổ trợ) - GIỮ NGUYÊN 100% DNA CỦA NGUYỆT
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    [NÂNG CẤP INDUSTRIAL]
    Autocomplete thần tốc hỗ trợ cả chuỗi đơn và chuỗi nhiều tên (cách nhau bởi dấu phẩy).
    """
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        if "," in current:
            parts = current.split(",")
            to_complete = parts[-1].strip().lower()
            prefix = ",".join(parts[:-1]) + ", "
        else:
            to_complete = current.strip().lower()
            prefix = ""

        choices = [
            app_commands.Choice(name=f"{prefix}{name}", value=f"{prefix}{name}") 
            for name in names if to_complete in name.lower()
        ][:25]
        return choices
    except Exception:
        return []

async def staff_role_autocomplete(interaction: discord.Interaction, current: str):
    """
    [INDUSTRIAL AUTOCOMPLETE]
    Bốc danh sách Role staff đang có trong cấu hình để sếp dễ dàng chọn gỡ bỏ.
    """
    guild = interaction.guild
    config = await get_ticket_config(guild.id)
    if not config or not config.get("staff_roles"): return []
    
    staff_ids = config.get("staff_roles", [])
    choices = []
    for r_id in staff_ids:
        role = guild.get_role(int(r_id))
        role_name = role.name if role else f"Unknown Role ({r_id})"
        if current.lower() in role_name.lower() or current in r_id:
            choices.append(app_commands.Choice(name=f"❌ {role_name}", value=r_id))
    return choices[:25]

class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="Hệ thống hỗ trợ và quản lý Ticket")

    def _sanitize(self, text): 
        if not text: return ""
        return re.sub(r'\D', '', text)

    # =========================
    # LỆNH 1: SETUP (Hạ tầng - Không làm mất dữ liệu nhân sự)
    # =========================
    @app_commands.command(name="setup", description="Khởi tạo hạ tầng Ticket (Danh mục & Kênh log)")
    @app_commands.describe(
        category_id="1. ID danh mục hoặc Tag danh mục chứa Ticket",
        log_channel_id="2. ID kênh hoặc Tag kênh gửi transcript"
    )
    async def setup_ticket(self, interaction: discord.Interaction, category_id: str, log_channel_id: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        clean_cat_id = self._sanitize(category_id)
        clean_log_id = self._sanitize(log_channel_id)

        try:
            cat = guild.get_channel(int(clean_cat_id)) if clean_cat_id else None
            log = guild.get_channel(int(clean_log_id)) if clean_log_id else None
            
            if not cat or not log:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                    description=f"**yiyi** không tìm thấy kênh hoặc danh mục hợp lệ. cậu hãy kiểm tra lại ID nhé.",
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

        # [ATK - BẢO TỒN DỮ LIỆU] Load config cũ để giữ lại Staff Roles và Embed đã gắn
        config = await get_ticket_config(guild.id) or {}
        config.update({
            "category_id": clean_cat_id,
            "log_channel_id": clean_log_id
        })
        
        if await update_ticket_config(guild.id, config):
            embed_res = discord.Embed(
                title=f"{Emojis.MATTRANG} cập nhật hạ tầng Ticket thành công",
                description=(
                    f"• danh mục: `{cat.name}`\n"
                    f"• kênh logs: `{log.name}`\n\n"
                    f"*sử dụng `/p ticket staff-add` để thêm nhân sự hỗ trợ nhee.*"
                ),
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed_res)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Không thể lưu cấu hình vào Cloud Atlas.")

    # =========================
    # LỆNH 2: STAFF-ADD (Thêm lũy tiến - Chống ghi đè)
    # =========================
    @app_commands.command(name="staff-add", description="Thêm role nhân viên hỗ trợ (Nhập nhiều cách nhau bởi dấu phẩy)")
    @app_commands.describe(roles="ID hoặc Tag các role muốn thêm (vd: ID1, ID2)")
    async def staff_add(self, interaction: discord.Interaction, roles: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        raw_parts = re.split(r'[/,\s]+', roles)
        new_ids = [self._sanitize(p) for p in raw_parts if self._sanitize(p)]
        
        valid_objs = []
        for r_id in new_ids:
            role = guild.get_role(int(r_id))
            if role: valid_objs.append(role)

        if not valid_objs:
            return await interaction.followup.send(f"{Emojis.HOICHAM} hổng thấy role nào hợp lệ để thêm hết á.")

        # [ATK - MẠCH CẬP NHẬT LŨY TIẾN]
        config = await get_ticket_config(guild.id) or {}
        current_staff = config.get("staff_roles", [])
        
        # Hợp nhất danh sách cũ và mới, gạt bỏ trùng lặp
        updated_staff = list(set(current_staff + [str(r.id) for r in valid_objs]))
        config["staff_roles"] = updated_staff
        
        if await update_ticket_config(guild.id, config):
            role_mentions = "\n".join([f"• {r.mention}" for r in valid_objs])
            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} cập nhật nhân sự thành công",
                description=f"**yiyi** đã thêm các role sau vào danh sách hỗ trợ:\n{role_mentions}",
                color=0xf8bbd0
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Không thể nạp dữ liệu lên Cloud.")

    # =========================
    # LỆNH 3: STAFF-REMOVE (Sa thải chính xác)
    # =========================
    @app_commands.command(name="staff-remove", description="Xóa role nhân viên khỏi hệ thống hỗ trợ")
    @app_commands.describe(role_id="Chọn role muốn xóa từ danh sách gợi ý")
    @app_commands.autocomplete(role_id=staff_role_autocomplete)
    async def staff_remove(self, interaction: discord.Interaction, role_id: str):
        await interaction.response.defer(ephemeral=True)
        
        clean_id = self._sanitize(role_id)
        config = await get_ticket_config(interaction.guild.id) or {}
        current_staff = config.get("staff_roles", [])
        
        if clean_id in current_staff:
            current_staff.remove(clean_id)
            config["staff_roles"] = current_staff
            
            if await update_ticket_config(interaction.guild.id, config):
                role = interaction.guild.get_role(int(clean_id))
                embed = discord.Embed(
                    description=f"{Emojis.MATTRANG} đã gỡ bỏ quyền hỗ trợ của role `{role.name if role else clean_id}` nhee.",
                    color=0xf8bbd0
                )
                return await interaction.followup.send(embed=embed)
        
        await interaction.followup.send(f"{Emojis.HOICHAM} Role này hổng có trong danh sách hỗ trợ nên hổng xóa được nhe.")

    # =========================
    # CÁC LỆNH KHÁC (GIỮ NGUYÊN DNA CỦA SẾP)
    # =========================
    @app_commands.command(name="apply", description="Liên kết Ticket vào Embed")
    @app_commands.describe(embed_name="Tên embed muốn gắn nút Ticket")
    @app_commands.autocomplete(embed_name=embed_name_autocomplete)
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
            "type": "button", "style": "primary", "label": "Ticket",
            "emoji": f"{Emojis.MATTRANG}", "custom_id": "yiyi:ticket:open", "system": "ticket"
        }

        updated = await atomic_update_button(guild_id, embed_name, action="update_by_id", custom_id="yiyi:ticket:open", button_data=btn_data)
        if not updated:
            await atomic_update_button(guild_id, embed_name, button_data=btn_data, action="add")

        config["embed_name"] = str(embed_name)
        await update_ticket_config(guild_id, config)

        embed_ok = discord.Embed(
            title=f"{Emojis.MATTRANG} liên kết Ticket vào embed `{embed_name}` thành công.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_ok)

    @app_commands.command(name="setting", description="Xem cấu hình hiện tại của hệ thống Ticket")
    async def ticket_setting(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        config = await get_ticket_config(guild.id)

        if not config:
            return await interaction.followup.send(f"{Emojis.HOICHAM} hệ thống ticket chưa được cấu hình trên server này.", ephemeral=True)

        embed_name = config.get("embed_name")
        display_embed = "Chưa liên kết"
        if embed_name:
            exists = await load_embed(guild.id, embed_name)
            if not exists:
                display_embed = f"`{embed_name}` (⚠️ **Đã bị xoá**)"
                config["embed_name"] = None
                await update_ticket_config(guild.id, config)
            else:
                display_embed = f"`{embed_name}`"

        cat = guild.get_channel(int(config.get("category_id", 0)))
        log = guild.get_channel(int(config.get("log_channel_id", 0)))
        staff_ids = config.get("staff_roles", [])
        staff_mentions = ", ".join([f"<@&{r}>" for r in staff_ids]) or "Chưa có"

        embed_setting = discord.Embed(
            title=f"{Emojis.MATTRANG} cấu hình ticket của `{guild.name}`",
            description=(
                f"• **Danh mục:** {cat.mention if cat else '`Không tìm thấy`'}\n"
                f"• **Kênh Logs:** {log.mention if log else '`Không tìm thấy`'}\n"
                f"• **Staff Roles:** {staff_mentions}\n"
                f"• **Embed liên kết:** {display_embed}"
            ),
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_setting)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "ticket"), None)
        if existing: p_cmd.remove_command("ticket")
        p_cmd.add_command(TicketGroup())
        print("[LOAD] Success: commands.ticket.ticket_group (Modular Staff Optimized)", flush=True)
