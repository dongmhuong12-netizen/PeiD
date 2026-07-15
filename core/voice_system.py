import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from core.voice_storage import (
    get_all_stations, get_station, upsert_station, delete_station,
    get_active_voice, add_active_voice, remove_active_voice, update_voice_owner
)
from core.status_storage import get_peid_data, update_peid_data
from utils.emojis import Emojis

# --- CẤU HÌNH GOD MODE ---
NGUYET_ID = 1055476307372294155 # ID Quyền lực tuyệt đối của Sếp

async def is_peid_vip(member: discord.Member) -> tuple[bool, str]:
    """Xác thực hệ thống Đặc quyền (Đã bọc God Mode & Khóa Server)"""
    if member.id == NGUYET_ID: 
        return True, ""
        
    data = await get_peid_data()
    vip_users = data.get("users", [])
    vip_roles = data.get("roles", [])
    
    # Quét xem Server này đã có Role nào được add vào list VIP chưa
    configured_roles_in_guild = [r for r in member.guild.roles if r.id in vip_roles]
    
    # Lớp khiên 1: Nếu Server chưa từng set Role đặc quyền nào, và User cũng không nằm trong list User VIP
    if not configured_roles_in_guild and member.id not in vip_users:
        return False, f"{Emojis.HOICHAM} Hệ thống: Kênh thoại đặc quyền chưa được thiết lập Role cấp phép tại máy chủ này."
        
    # Lớp khiên 2: User có nằm trong danh sách VIP tay không?
    if member.id in vip_users: 
        return True, ""
        
    # Lớp khiên 3: User có cầm Role VIP của Server này không?
    for role in member.roles:
        if role.id in vip_roles: 
            return True, ""
            
    return False, f"{Emojis.HOICHAM} Lỗi: Quyền truy cập bị từ chối. Bạn không sở hữu Role Đặc quyền của hệ thống."

def get_default_panel_embed() -> discord.Embed:
    desc = (
        f"{Emojis.RENAME} — **Đổi tên** kênh thoại\n"
        f"{Emojis.LIMIT} — **Giới hạn** người tham gia\n"
        f"{Emojis.LOCK} — **Khóa** kênh (Từ chối kết nối)\n"
        f"{Emojis.UNLOCK} — **Mở khóa** kênh (Cho phép kết nối)\n"
        f"{Emojis.CLAIM} — **Đoạt quyền** Chủ phòng\n\n"
        f"{Emojis.GHOST} — **Ẩn** kênh thoại (Vô hình)\n"
        f"{Emojis.REVEAL} — **Hiện** kênh thoại (Công khai)\n"
        f"{Emojis.KICK} — **Đuổi** người dùng\n"
        f"{Emojis.BLOCK} — **Chặn** người dùng\n"
        f"{Emojis.UNBLOCK} — **Gỡ chặn** người dùng\n\n"
        f"{Emojis.OWN} — **Chuyển quyền** Chủ phòng\n"
        f"{Emojis.STTUS} — **Đổi trạng thái** (Đặc quyền peiD)\n"
        f"{Emojis.PERMANENT} — **Kênh Vĩnh Viễn** (Đặc quyền peiD)"
    )
    return discord.Embed(title="Bảng Điều Khiển Kênh Thoại", description=desc, color=0x2b2d31)


# ====================================================
# MODULE 1: FORM NHẬP LIỆU CƠ BẢN (MODALS)
# ====================================================
class RenameModal(discord.ui.Modal, title='Cập Nhật Tên Kênh'):
    name_input = discord.ui.TextInput(
        label='Tên kênh mới',
        style=discord.TextStyle.short,
        placeholder='Nhập tên kênh...',
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.user.voice.channel
        await vc.edit(name=self.name_input.value)
        await interaction.response.send_message(f"{Emojis.BUOMA} Cập nhật tên kênh thành công.", ephemeral=True)

class LimitModal(discord.ui.Modal, title='Cập Nhật Giới Hạn Người'):
    limit_input = discord.ui.TextInput(
        label='Số người (0-99, 0 là vô hạn)',
        style=discord.TextStyle.short,
        placeholder='0',
        required=True,
        max_length=2
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.limit_input.value)
            if not (0 <= limit <= 99): 
                raise ValueError
            vc = interaction.user.voice.channel
            await vc.edit(user_limit=limit)
            await interaction.response.send_message(f"{Emojis.BUOMA} Cập nhật giới hạn thành {limit} người.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi định dạng. Yêu cầu nhập số từ 0 đến 99.", ephemeral=True)


# ====================================================
# MODULE 2: HỆ THỐNG MENU CHỌN THÀNH VIÊN (2 LUỒNG LOGIC)
# ====================================================
class InternalActionSelect(discord.ui.Select):
    def __init__(self, action: str, vc: discord.VoiceChannel):
        self.action = action
        self.vc = vc
        options = []
        
        for m in vc.members:
            options.append(discord.SelectOption(label=m.display_name, value=str(m.id)))
        if not options:
            options.append(discord.SelectOption(label="Kênh hiện tại trống", value="none"))
                
        options = options[:25]
        super().__init__(placeholder="Chọn thành viên đang trong phòng...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Không có mục tiêu hợp lệ.", ephemeral=True)
            
        target = interaction.guild.get_member(int(self.values[0]))
        if not target: 
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Người dùng không tồn tại.", ephemeral=True)
            
        if target.id == interaction.user.id and self.action != "own":
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Từ chối thao tác lên bản thân.", ephemeral=True)
        
        try:
            if self.action == "kick":
                if target in self.vc.members: await target.move_to(None)
                await interaction.response.send_message(f"{Emojis.BUOMA} Ngắt kết nối {target.mention} thành công.", ephemeral=True)
            
            elif self.action == "own":
                await update_voice_owner(self.vc.id, target.id)
                await self.vc.set_permissions(target, view_channel=True, send_messages=True, speak=True)
                await interaction.response.send_message(f"{Emojis.BUOMA} Chuyển quyền Chủ phòng cho {target.mention} hoàn tất.", ephemeral=True)
                
            await interaction.message.delete()
        except discord.Forbidden:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Thiếu quyền hạn thao tác từ Discord.", ephemeral=True)


class GlobalUserSelect(discord.ui.UserSelect):
    def __init__(self, action: str, vc: discord.VoiceChannel):
        self.action = action
        self.vc = vc
        super().__init__(placeholder="Tìm kiếm bằng tên hoặc ID...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        target = self.values[0]
        
        if isinstance(target, discord.User):
            target = interaction.guild.get_member(target.id)
            
        if not target:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Người dùng không thuộc máy chủ này.", ephemeral=True)
            
        if target.id == interaction.user.id:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Từ chối thao tác lên bản thân.", ephemeral=True)

        try:
            if self.action == "block":
                await self.vc.set_permissions(target, connect=False)
                if target in self.vc.members: await target.move_to(None)
                await interaction.response.send_message(f"{Emojis.BUOMA} Thiết lập chặn truy cập đối với {target.mention} hoàn tất.", ephemeral=True)
            
            elif self.action == "unblock":
                await self.vc.set_permissions(target, overwrite=None)
                await interaction.response.send_message(f"{Emojis.BUOMA} Thu hồi lệnh chặn đối với {target.mention} hoàn tất.", ephemeral=True)
                
            await interaction.message.delete()
        except discord.Forbidden:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Thiếu quyền hạn thao tác từ hệ thống.", ephemeral=True)


class ActionView(discord.ui.View):
    def __init__(self, action: str, vc: discord.VoiceChannel):
        super().__init__(timeout=60)
        if action in ["kick", "own"]:
            self.add_item(InternalActionSelect(action, vc))
        elif action in ["block", "unblock"]:
            self.add_item(GlobalUserSelect(action, vc))


# ====================================================
# MODULE 3: GIAO DIỆN NÚT BẤM CỐ ĐỊNH (13 NÚT)
# ====================================================
class VoiceControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def verify_owner(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu tham gia kênh thoại.", ephemeral=True)
            return False
            
        vc_data = await get_active_voice(user.voice.channel.id)
        if not vc_data:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Kênh không thuộc dữ liệu tạm thời.", ephemeral=True)
            return False
            
        if vc_data["owner_id"] != user.id and user.id != NGUYET_ID:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Quyền truy cập bị từ chối.", ephemeral=True)
            return False
            
        return True

    # --- HÀNG 1 ---
    @discord.ui.button(label="", emoji=Emojis.RENAME, custom_id="vcp_rename", row=0)
    async def btn_rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="", emoji=Emojis.LIMIT, custom_id="vcp_limit", row=0)
    async def btn_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        await interaction.response.send_modal(LimitModal())

    @discord.ui.button(label="", emoji=Emojis.LOCK, custom_id="vcp_lock", row=0)
    async def btn_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message(f"{Emojis.BUOMA} Thiết lập khóa kênh hoàn tất.", ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.UNLOCK, custom_id="vcp_unlock", row=0)
    async def btn_unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, connect=None)
        await interaction.response.send_message(f"{Emojis.BUOMA} Thiết lập mở khóa kênh hoàn tất.", ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.CLAIM, custom_id="vcp_claim", row=0)
    async def btn_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu tham gia kênh thoại.", ephemeral=True)
            
        vc = user.voice.channel
        vc_data = await get_active_voice(vc.id)
        if not vc_data:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Kênh không thuộc dữ liệu tạm thời.", ephemeral=True)

        owner_in_vc = any(m.id == vc_data["owner_id"] for m in vc.members)
        if owner_in_vc and user.id != NGUYET_ID:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu đoạt quyền thất bại do Chủ phòng đang hoạt động.", ephemeral=True)
            
        await update_voice_owner(vc.id, user.id)
        await vc.set_permissions(user, view_channel=True, send_messages=True, speak=True)
        await interaction.response.send_message(f"{Emojis.BUOMA} Đoạt quyền Chủ phòng thành công.", ephemeral=True)

    # --- HÀNG 2 ---
    @discord.ui.button(label="", emoji=Emojis.GHOST, custom_id="vcp_ghost", row=1)
    async def btn_ghost(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message(f"{Emojis.BUOMA} Kích hoạt tàng hình kênh hoàn tất.", ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.REVEAL, custom_id="vcp_reveal", row=1)
    async def btn_reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.guild.default_role, view_channel=None)
        await interaction.response.send_message(f"{Emojis.BUOMA} Kích hoạt hiển thị kênh hoàn tất.", ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.KICK, custom_id="vcp_kick", row=1)
    async def btn_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await interaction.response.send_message("Hệ thống: Chọn thành viên ngắt kết nối.", view=ActionView("kick", vc), ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.BLOCK, custom_id="vcp_block", row=1)
    async def btn_block(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await interaction.response.send_message("Hệ thống: Vui lòng nhập Tên hoặc ID mục tiêu để chặn.", view=ActionView("block", vc), ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.UNBLOCK, custom_id="vcp_unblock", row=1)
    async def btn_unblock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await interaction.response.send_message("Hệ thống: Vui lòng nhập Tên hoặc ID mục tiêu để gỡ chặn.", view=ActionView("unblock", vc), ephemeral=True)

    # --- HÀNG 3 ---
    @discord.ui.button(label="", emoji=Emojis.OWN, custom_id="vcp_own", row=2)
    async def btn_own(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        vc = interaction.user.voice.channel
        await interaction.response.send_message("Hệ thống: Chọn thành viên tiếp nhận quyền Chủ phòng.", view=ActionView("own", vc), ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.STTUS, custom_id="vcp_status", row=2)
    async def btn_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        
        is_vip, err_msg = await is_peid_vip(interaction.user)
        if not is_vip:
            return await interaction.response.send_message(err_msg, ephemeral=True)
            
        await interaction.response.send_message(
            f"{Emojis.BUOMA} Vui lòng nhập nội dung trạng thái mới vào kênh văn bản này trong 60 giây.\n"
            "*(Lệnh hủy: `cancel` | Lệnh xóa trạng thái: `clear`)*", 
            ephemeral=True
        )

        def check_msg(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for('message', check=check_msg, timeout=60.0)
            try: 
                await msg.delete()
            except: 
                pass
                
            content = msg.content
            if content.lower() == 'cancel':
                return await interaction.followup.send(f"{Emojis.BUOMA} Thao tác đã bị hủy.", ephemeral=True)
                
            vc = interaction.user.voice.channel
            if content.lower() == 'clear':
                await vc.edit(status=None)
                return await interaction.followup.send(f"{Emojis.BUOMA} Đã xóa trạng thái kênh.", ephemeral=True)

            if re.search(r"http[s]?://", content.lower()):
                return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Nội dung chứa liên kết không hợp lệ.", ephemeral=True)

            await vc.edit(status=content)
            await interaction.followup.send(f"{Emojis.BUOMA} Cập nhật trạng thái thành công.", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Quá thời gian phản hồi.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Thiếu quyền hạn thiết lập trạng thái.", ephemeral=True)

    @discord.ui.button(label="", emoji=Emojis.PERMANENT, custom_id="vcp_permanent", row=2)
    async def btn_permanent(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.verify_owner(interaction): return
        
        is_vip, err_msg = await is_peid_vip(interaction.user)
        if not is_vip:
            return await interaction.response.send_message(err_msg, ephemeral=True)
            
        vc = interaction.user.voice.channel
        await vc.set_permissions(interaction.user, manage_channels=True)
        await remove_active_voice(vc.id)
        await interaction.response.send_message(f"{Emojis.BUOMA} Chuyển đổi trạng thái Vĩnh viễn hoàn tất. Yiyi ngừng giám sát dữ liệu.", ephemeral=True)


# ====================================================
# MODULE 4: HỆ THỐNG LỆNH ĐẶC QUYỀN (/peid_vc)
# ====================================================
class PeidSystemGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="peid_vc", description="Hệ thống Quản lý Đặc quyền")

    @app_commands.command(name="premium", description="Cấp đặc quyền cho Người dùng hoặc Vai trò")
    @app_commands.default_permissions(administrator=True)
    async def peid_premium(self, interaction: discord.Interaction, user: discord.Member = None, role: discord.Role = None):
        if not user and not role:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu chỉ định Người dùng hoặc Vai trò.", ephemeral=True)
            
        # Lớp bảo mật: Chống gán @everyone
        if role and role.id == interaction.guild.id:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Hệ thống từ chối: Lỗ hổng bảo mật. Không được phép cấp thẻ VIP cho toàn bộ Server (@everyone).", ephemeral=True)
            
        data = await get_peid_data()
        if user and user.id not in data["users"]: 
            data["users"].append(user.id)
        if role and role.id not in data["roles"]: 
            data["roles"].append(role.id)
            
        await update_peid_data(data["users"], data["roles"])
        await interaction.response.send_message(f"{Emojis.BUOMA} Cấp phát đặc quyền thành công.", ephemeral=True)

    @app_commands.command(name="revoke", description="Thu hồi đặc quyền")
    @app_commands.default_permissions(administrator=True)
    async def peid_revoke(self, interaction: discord.Interaction, user: discord.Member = None, role: discord.Role = None):
        if not user and not role:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu chỉ định Người dùng hoặc Vai trò.", ephemeral=True)
            
        data = await get_peid_data()
        if user and user.id in data["users"]: 
            data["users"].remove(user.id)
        if role and role.id in data["roles"]: 
            data["roles"].remove(role.id)
            
        await update_peid_data(data["users"], data["roles"])
        await interaction.response.send_message(f"{Emojis.BUOMA} Thu hồi đặc quyền thành công.", ephemeral=True)

    @app_commands.command(name="status", description="Cập nhật trạng thái Kênh Thoại (Không giới hạn phòng)")
    async def peid_status(self, interaction: discord.Interaction, noi_dung: str = None):
        is_vip, err_msg = await is_peid_vip(interaction.user)
        if not is_vip:
            return await interaction.response.send_message(err_msg, ephemeral=True)
            
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu tham gia kênh thoại.", ephemeral=True)
            
        vc = interaction.user.voice.channel
        
        if not noi_dung:
            await vc.edit(status=None)
            return await interaction.response.send_message(f"{Emojis.BUOMA} Đã xóa trạng thái kênh.", ephemeral=True)
            
        if re.search(r"http[s]?://", noi_dung.lower()):
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Nội dung chứa liên kết không hợp lệ.", ephemeral=True)
            
        try:
            await vc.edit(status=noi_dung)
            await interaction.response.send_message(f"{Emojis.BUOMA} Cập nhật trạng thái thành công.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Thiếu quyền hạn thao tác từ hệ thống.", ephemeral=True)

    @app_commands.command(name="permanent", description="Chuyển đổi Kênh Tạm thời thành Kênh Vĩnh viễn")
    async def peid_permanent(self, interaction: discord.Interaction):
        is_vip, err_msg = await is_peid_vip(interaction.user)
        if not is_vip:
            return await interaction.response.send_message(err_msg, ephemeral=True)
            
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu tham gia kênh thoại.", ephemeral=True)
            
        vc = interaction.user.voice.channel
        vc_data = await get_active_voice(vc.id)
        if not vc_data:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Kênh không thuộc dữ liệu tạm thời.", ephemeral=True)
            
        if vc_data["owner_id"] != interaction.user.id and interaction.user.id != NGUYET_ID:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Yêu cầu quyền Chủ phòng.", ephemeral=True)

        await vc.set_permissions(interaction.user, manage_channels=True)
        await remove_active_voice(vc.id)
        await interaction.response.send_message(f"{Emojis.BUOMA} Chuyển đổi trạng thái Vĩnh viễn hoàn tất.", ephemeral=True)


# ====================================================
# MODULE 5: LÕI SỰ KIỆN VOICE & ADMIN SETUP TRẠM
# ====================================================
class VoiceSystemCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(VoiceControlPanel())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel: 
            return

        if after.channel:
            stations = await get_all_stations()
            for st in stations:
                if after.channel.id == st.get("creator_vc"):
                    category = after.channel.category
                    name_format = st.get("name_format", "🔊 {user}")
                    vc_name = name_format.replace("{user}", member.display_name).replace("{username}", member.name)
                    
                    try:
                        # TẠO GÓI QUYỀN SẠCH CHẶN ĐỒNG BỘ TỪ DANH MỤC
                        overwrites = {
                            member.guild.default_role: discord.PermissionOverwrite(), # Reset @everyone về cơ bản
                            member.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_permissions=True, manage_roles=True, connect=True, move_members=True),
                            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, speak=True)
                        }
                        
                        new_vc = await category.create_voice_channel(name=vc_name, overwrites=overwrites)
                        await member.move_to(new_vc)
                        await add_active_voice(new_vc.id, member.id, category.id)
                    except discord.Forbidden:
                        pass
                    break

        if before.channel:
            vc_data = await get_active_voice(before.channel.id)
            if vc_data:
                if len(before.channel.members) == 0:
                    try:
                        await before.channel.delete()
                        await remove_active_voice(before.channel.id)
                    except discord.Forbidden:
                        pass
                else:
                    if member.id == vc_data["owner_id"]:
                        for m in before.channel.members:
                            if m.id == NGUYET_ID:
                                await update_voice_owner(before.channel.id, NGUYET_ID)
                                await before.channel.set_permissions(m, view_channel=True, send_messages=True, speak=True)
                                break

class VoiceAdminGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="voice", description="Quản lý Trạm Kênh Thoại Tạm Thời")

    @app_commands.command(name="setup", description="Khởi tạo hoặc cập nhật Trạm")
    @app_commands.default_permissions(administrator=True)
    async def voice_setup(self, interaction: discord.Interaction, danh_muc: discord.CategoryChannel, 
                          kenh_tao_voice: discord.VoiceChannel = None, kenh_bang_dieu_khien: discord.TextChannel = None):
        if not kenh_tao_voice and not kenh_bang_dieu_khien:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Thiếu tham số kênh đầu vào.", ephemeral=True)
            
        data = await get_station(danh_muc.id) or {}
        if kenh_tao_voice: 
            data["creator_vc"] = kenh_tao_voice.id
        if kenh_bang_dieu_khien: 
            data["control_tc"] = kenh_bang_dieu_khien.id
            await kenh_bang_dieu_khien.send(embed=get_default_panel_embed(), view=VoiceControlPanel())
        
        await upsert_station(danh_muc.id, data)
        await interaction.response.send_message(f"{Emojis.BUOMA} Cập nhật dữ liệu Trạm thành công.", ephemeral=True)

    @app_commands.command(name="link_embed", description="Sao chép Giao diện Embed tùy chỉnh")
    @app_commands.default_permissions(administrator=True)
    async def voice_link_embed(self, interaction: discord.Interaction, danh_muc: discord.CategoryChannel, 
                               kenh_mau: discord.TextChannel, message_id_mau: str):
        await interaction.response.defer(ephemeral=True)
        
        station = await get_station(danh_muc.id)
        if not station or not station.get("control_tc"):
            return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Kênh điều khiển chưa được thiết lập.")

        target_channel = interaction.guild.get_channel(station["control_tc"])
        if not target_channel:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Không thể định vị Kênh điều khiển.")

        try:
            msg = await kenh_mau.fetch_message(int(message_id_mau))
            if not msg.embeds:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi: Dữ liệu mẫu không chứa Embed.")
                
            await target_channel.send(embeds=msg.embeds, view=VoiceControlPanel())
            await interaction.followup.send(f"{Emojis.BUOMA} Đồng bộ Giao diện thành công.")
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi hệ thống: Xử lý gián đoạn.")

    @app_commands.command(name="rename_format", description="Thiết lập định dạng Tên kênh")
    @app_commands.default_permissions(administrator=True)
    async def voice_format(self, interaction: discord.Interaction, danh_muc: discord.CategoryChannel, mau_ten: str):
        data = await get_station(danh_muc.id)
        if not data:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} Lỗi: Danh mục chưa được liên kết Trạm.", ephemeral=True)
            
        data["name_format"] = mau_ten
        await upsert_station(danh_muc.id, data)
        await interaction.response.send_message(f"{Emojis.BUOMA} Cập nhật định dạng tên hoàn tất.", ephemeral=True)

    @app_commands.command(name="remove", description="Xóa dữ liệu Trạm khỏi hệ thống")
    @app_commands.default_permissions(administrator=True)
    async def voice_remove(self, interaction: discord.Interaction, danh_muc: discord.CategoryChannel):
        await delete_station(danh_muc.id)
        await interaction.response.send_message(f"{Emojis.BUOMA} Tháo dỡ Trạm thành công.", ephemeral=True)

async def setup(bot: commands.Bot):
    bot.tree.add_command(VoiceAdminGroup())
    bot.tree.add_command(PeidSystemGroup())
    await bot.add_cog(VoiceSystemCog(bot))
    print("[load] success: core.voice_system (Final Build - Ultimate God Mode)")
