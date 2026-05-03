import discord
from discord import app_commands
from discord.ext import commands
import re
import copy

from core.embed_storage import load_embed, get_all_embed_names, atomic_update_button
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER
# =============================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên embed chuẩn Multi-server"""
    guild = interaction.guild
    if not guild: return []
    names = await get_all_embed_names(guild.id)
    return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]

# =============================
# MODAL 1: NÚT LINK (BASIC) - GIỮ NGUYÊN 100%
# =============================
class LinkButtonModal(discord.ui.Modal, title="Cài đặt Nút Link (Chuyển hướng)"):
    label = discord.ui.TextInput(
        label="Nhãn hiển thị trên nút",
        placeholder="Ví dụ: Tham gia ngay, Group hỗ trợ...",
        min_length=1, max_length=80, required=True
    )
    url = discord.ui.TextInput(
        label="Đường dẫn Link (URL)",
        placeholder="https://discord.gg/peid",
        required=True
    )

    def __init__(self, embed_name: str):
        super().__init__()
        self.embed_name = embed_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if not re.match(r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', self.url.value):
            return await interaction.followup.send(f"{Emojis.HOICHAM} URL không hợp lệ! Hãy bắt đầu bằng `http://` hoặc `https://` nhé.")

        btn_data = {"type": "link", "label": self.label.value, "url": self.url.value}
        
        success = await atomic_update_button(interaction.guild.id, self.embed_name, btn_data, action="add")
        if not success:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi! Embed `{self.embed_name}` không tồn tại hoặc đã đầy (Max 25 nút).")

        embed_success = discord.Embed(
            title=f"{Emojis.YIYITIM} Đã gắn nút Link thành công!",
            description=f"Embed `{self.embed_name}` đã nhận nút: **{self.label.value}**",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_success)

# =============================
# MODAL 2: NÚT ROLE (PHẢN XẠ) - GIỮ NGUYÊN 100%
# =============================
class RoleButtonModal(discord.ui.Modal, title="Cài đặt Nút Nhận Role"):
    label = discord.ui.TextInput(
        label="Nhãn hiển thị", placeholder="Ví dụ: Nhận Role Thông Báo", max_length=80, required=True
    )
    role_id = discord.ui.TextInput(
        label="ID Role (Cấp khi bấm)", placeholder="123456789012345678", min_length=17, max_length=20, required=True
    )
    style = discord.ui.TextInput(
        label="Màu nút (1:Xanh, 2:Xám, 3:Lục, 4:Đỏ)", placeholder="1", default="1", max_length=1, required=True
    )

    def __init__(self, embed_name: str):
        super().__init__()
        self.embed_name = embed_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.role_id.value.isdigit():
            return await interaction.followup.send(f"{Emojis.HOICHAM} ID Role chỉ được chứa số!")

        style_val = int(self.style.value) if self.style.value.isdigit() and self.style.value in ["1","2","3","4"] else 1
        
        btn_data = {
            "type": "button", "style": style_val, "label": self.label.value,
            "custom_id": f"yiyi:role:{self.role_id.value}"
        }
        
        success = await atomic_update_button(interaction.guild.id, self.embed_name, btn_data, action="add")
        if success:
            embed_success = discord.Embed(title=f"{Emojis.MATTRANG} Đã gắn nút Role thành công!", description=f"Embed `{self.embed_name}` đã nhận nút: **{self.label.value}**", color=0xf8bbd0)
            await interaction.followup.send(embed=embed_success)
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Có lỗi xảy ra, chắc là đầy nút rồi!")

# =============================
# MODAL 3: NÚT TICKET (HỖ TRỢ) - GIỮ NGUYÊN 100%
# =============================
class TicketButtonModal(discord.ui.Modal, title="Cài đặt Nút Mở Ticket"):
    label = discord.ui.TextInput(label="Nhãn hiển thị", placeholder="Mở Ticket Hỗ Trợ", max_length=80, required=True)
    staff_id = discord.ui.TextInput(label="ID Role Staff quản lý", placeholder="123456789...", required=True)

    def __init__(self, embed_name: str):
        super().__init__()
        self.embed_name = embed_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.staff_id.value.isdigit():
            return await interaction.followup.send(f"{Emojis.HOICHAM} ID Role chỉ được chứa số!")

        btn_data = {"type": "button", "style": 2, "label": self.label.value, "custom_id": f"yiyi:ticket:{self.staff_id.value}", "emoji": "🎫"}
        success = await atomic_update_button(interaction.guild.id, self.embed_name, btn_data, action="add")
        if success:
            await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.MATTRANG} Đã gắn nút Ticket thành công!", color=0xf8bbd0))

# =============================
# MODAL 4: NÚT VERIFY (BẢO MẬT) - GIỮ NGUYÊN 100%
# =============================
class VerifyButtonModal(discord.ui.Modal, title="Cài đặt Nút Verify (Xác thực)"):
    label = discord.ui.TextInput(label="Nhãn hiển thị", placeholder="Xác nhận thành viên", max_length=80, required=True)
    mem_id = discord.ui.TextInput(label="ID Role Thành viên", placeholder="123456789...", required=True)

    def __init__(self, embed_name: str):
        super().__init__()
        self.embed_name = embed_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        btn_data = {"type": "button", "style": 3, "label": self.label.value, "custom_id": f"yiyi:verify:{self.mem_id.value}", "emoji": "✅"}
        success = await atomic_update_button(interaction.guild.id, self.embed_name, btn_data, action="add")
        if success:
            await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.MATTRANG} Đã gắn nút Verify thành công!", color=0xf8bbd0))

# =============================
# [THÊM MỚI] MODAL 5: HỆ THỐNG TƯƠNG TÁC LẺ (GACHA/VOTE/SECRET/REFRESH/DISMISS)
# =============================
class InteractionButtonModal(discord.ui.Modal, title="Cấu hình Tương tác Omni"):
    label = discord.ui.TextInput(label="Nhãn hiển thị", placeholder="Ví dụ: Thử vận may", max_length=80, required=True)
    data = discord.ui.TextInput(
        label="Dữ liệu đi kèm (Tin nhắn ẩn/ID Vote)", 
        placeholder="Nhập nội dung nếu là Secret Message, hoặc ID nếu là Vote...",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, embed_name: str, itype: str):
        super().__init__()
        self.embed_name = embed_name
        self.itype = itype # secret, gacha, vote, refresh, dismiss

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Tokenization: Nén dữ liệu (Thay dấu cách bằng gạch dưới để CustomID không bị ngắt)
        clean_data = self.data.value.replace(" ", "_") if self.data.value else "none"
        
        btn_data = {
            "type": "button", "style": 2, "label": self.label.value,
            "custom_id": f"yiyi:interaction:{self.itype}:{clean_data}"
        }
        
        if await atomic_update_button(interaction.guild.id, self.embed_name, btn_data, action="add"):
            await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.YIYITIM} Đã gắn tương tác `{self.itype}` thành công!", color=0xf8bbd0))

# =============================
# LỆNH THAO TÁC (COMMANDS)
# =============================

@app_commands.command(name="link", description="gắn nút link (chuyển hướng web)")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_link_cmd(interaction: discord.Interaction, name: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.send_modal(LinkButtonModal(name))

@app_commands.command(name="role", description="gắn nút nhận role (tự động cấp role)")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_role_cmd(interaction: discord.Interaction, name: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.send_modal(RoleButtonModal(name))

@app_commands.command(name="ticket", description="gắn nút mở kênh ticket hỗ trợ riêng")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_ticket_cmd(interaction: discord.Interaction, name: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.send_modal(TicketButtonModal(name))

@app_commands.command(name="verify", description="gắn nút xác thực cổng an ninh")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_verify_cmd(interaction: discord.Interaction, name: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.send_modal(VerifyButtonModal(name))

# --- [THÊM MỚI] LỆNH OMNI-INTERACTION ---
@app_commands.command(name="interaction", description="gắn các nút tương tác đặc biệt (gacha, vote, secret...)")
@app_commands.describe(type="loại tương tác muốn gắn")
@app_commands.choices(type=[
    app_commands.Choice(name="Secret Message (Tin nhắn ẩn)", value="secret"),
    app_commands.Choice(name="Gacha (Thử nhân phẩm)", value="gacha"),
    app_commands.Choice(name="Vote (Biểu quyết nhanh)", value="vote"),
    app_commands.Choice(name="Refresh (Cập nhật trạng thái)", value="refresh"),
    app_commands.Choice(name="Dismiss (Tự xóa tin nhắn)", value="dismiss")
])
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_interaction_cmd(interaction: discord.Interaction, name: str, type: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.send_modal(InteractionButtonModal(name, type))

# --- [THÊM MỚI] LỆNH MENU (SELECT ROLE) ---
@app_commands.command(name="menu", description="gắn menu thả xuống (dropdown) để chọn role chuyên nghiệp")
@app_commands.describe(roles="danh sách ID role ngăn cách bởi dấu phẩy", placeholder="lời nhắc trên menu")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_menu_cmd(interaction: discord.Interaction, name: str, roles: str, placeholder: str = "Chọn một tùy chọn..."):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    
    role_ids = [r.strip() for r in roles.split(",") if r.strip().isdigit()]
    if not role_ids: return await interaction.followup.send(f"{Emojis.HOICHAM} Danh sách ID role không hợp lệ!")

    options = []
    for rid in role_ids[:25]: # Giới hạn Discord Max 25 Options
        role = interaction.guild.get_role(int(rid))
        if role:
            options.append({"label": role.name, "value": str(role.id)})

    if not options: return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy Role nào từ ID sếp cung cấp!")

    btn_data = {
        "type": "select", "placeholder": placeholder,
        "custom_id": f"yiyi:menu:role_pick", "options": options
    }
    
    if await atomic_update_button(interaction.guild.id, name, btn_data, action="add"):
        await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.MATTRANG} Đã gắn Menu chọn Role thành công!", color=0xf8bbd0))

@app_commands.command(name="clear", description="xóa toàn bộ nút bấm khỏi embed")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def btn_clear_cmd(interaction: discord.Interaction, name: str):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(f"{Emojis.HOICHAM} Sếp chưa đủ quyền hạn!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    success = await atomic_update_button(interaction.guild.id, name, action="clear")
    if success:
        await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.MATTRANG} Đã dọn dẹp sạch sẽ nút trên `{name}`", color=0xf8bbd0))
    else:
        await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy embed này!")

# =============================
# INJECTION LOGIC (Hệ thống tiêm lệnh Multi-IT)
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        button_group = next((cmd for cmd in p_cmd.commands if cmd.name == "button" and isinstance(cmd, app_commands.Group)), None)
                
        if button_group:
            # Gỡ sạch lệnh cũ để nạp dàn vũ khí Phase 3 Full-Option
            all_cmds = ["link", "role", "ticket", "verify", "interaction", "menu", "clear"]
            for cmd_name in all_cmds:
                existing = next((c for c in button_group.commands if c.name == cmd_name), None)
                if existing: button_group.remove_command(cmd_name)
            
            # Tiêm dàn lệnh mới
            button_group.add_command(btn_link_cmd)
            button_group.add_command(btn_role_cmd)
            button_group.add_command(btn_ticket_cmd)
            button_group.add_command(btn_verify_cmd)
            button_group.add_command(btn_interaction_cmd) 
            button_group.add_command(btn_menu_cmd)        
            button_group.add_command(btn_clear_cmd)
            
            print("[load] success: commands.embed.embed_buttons (Phase 3 Full Option)", flush=True)
        else:
            print("[error] Phase 3: Không tìm thấy nhánh /p button (Kiểm tra lại core.root)", flush=True)
    else:
        print("[error] Phase 3: Khung lệnh /p chưa tồn tại.", flush=True)


