import discord
from discord.ext import commands
import asyncio
import datetime
import random

# IMPORT EMOJI HỆ THỐNG (Đồng bộ đồng nhất giao diện)
from utils.emojis import Emojis

class ButtonListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """
        trạm điều phối tương tác toàn cục (interaction gateway).
        chỉ xử lý các custom_id có tiền tố 'yiyi:' để tối ưu hóa hiệu năng xử lý sự kiện.
        """
        # Multi-IT: Early return để giải phóng tài nguyên nhanh nhất có thể
        custom_id = interaction.data.get("custom_id")
        if not custom_id or not str(custom_id).startswith("yiyi:"):
            return

        # PHÂN TÁCH TOKEN: yiyi:[hệ_thống:[loại/dữ_liệu]:[extra]
        # Đồng bộ 100% với định dạng custom_id tại commands/embed/embed_buttons.py
        parts = custom_id.split(":")
        if len(parts) < 3:
            return

        system_type = parts[1] # 'role', 'ticket', 'verify', 'interaction', 'menu'
        
        # --- OMNI-ROUTING (PHÂN LUỒNG TƯƠNG TÁC) ---
        
        # 1. HỆ THỐNG ROLE (TOGGLE ROLE)
        if system_type == "role":
            await self._execute_role_logic(interaction, parts[2])

        # 2. HỆ THỐNG TICKET (HỖ TRỢ TẠI CHỖ)
        elif system_type == "ticket":
            await self._execute_ticket_logic(interaction, parts[2])

        # 3. HỆ THỐNG VERIFY (CỔNG AN NINH)
        elif system_type == "verify":
            await self._execute_verify_logic(interaction, parts[2])

        # [THÊM MỚI] 4. HỆ THỐNG MENU (SELECT ROLE)
        elif system_type == "menu" and parts[2] == "role_pick":
            await self._execute_menu_role_logic(interaction)

        # [THÊM MỚI] 5. HỆ THỐNG TƯƠNG TÁC OMNI (GACHA, VOTE, SECRET, DISMISS, REFRESH)
        elif system_type == "interaction":
            await self._handle_extra_interactions(interaction, parts)

    # ----------------------------------------------
    # CHI TIẾT THỰC THI (ENTERPRISE LOGIC)
    # ----------------------------------------------

    async def _execute_role_logic(self, interaction: discord.Interaction, role_id: str):
        """Cơ chế Toggle Role (Tự động nhận/gỡ khi click)"""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        role = guild.get_role(int(role_id)) if role_id.isdigit() else None

        if not role:
            return await interaction.followup.send(f"{Emojis.HOICHAM} lỗi: role này không còn tồn tại hoặc id không hợp lệ.")

        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.followup.send(f"{Emojis.MATTRANG} đã gỡ role **{role.name}** khỏi cậu.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"{Emojis.YIYITIM} đã cấp role **{role.name}** cho cậu thành công!", ephemeral=True)
        except discord.Forbidden:
            # IT Pro: Xử lý lỗi phân tầng Role (Hierarchy Error)
            await interaction.followup.send(f"{Emojis.HOICHAM} yiyi thiếu quyền hạn! hãy báo admin đưa role của yiyi lên cao hơn role **{role.name}** nhé.", ephemeral=True)

    async def _execute_ticket_logic(self, interaction: discord.Interaction, staff_role_id: str):
        """Khởi tạo kênh hỗ trợ biệt lập (Privacy & Support)"""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        # Anti-Spam: Check trùng tên kênh để tránh tạo lặp
        clean_name = f"ticket-{user.name.lower()}".replace(" ", "-")
        if discord.utils.get(guild.channels, name=clean_name):
            return await interaction.followup.send(f"{Emojis.HOICHAM} cậu đã mở một ticket hỗ trợ rồi, hãy kiểm tra lại danh sách kênh nhé!", ephemeral=True)

        # Quyền hạn kênh: Chỉ User, Staff và Bot được xem
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        staff_role = guild.get_role(int(staff_role_id)) if staff_role_id.isdigit() else None
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Category Management: Tự động gom vào nhóm TICKETS
        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category:
            try: category = await guild.create_category("TICKETS")
            except: category = None

        channel = await guild.create_text_channel(name=clean_name, overwrites=overwrites, category=category)

        # UI trong Ticket: Nút đóng khẩn cấp
        class CloseButton(discord.ui.View):
            def __init__(self): super().__init__(timeout=None)
            @discord.ui.button(label="đóng ticket", style=discord.ButtonStyle.danger, emoji="🔒")
            async def close(self, it: discord.Interaction, btn):
                await it.response.send_message("kênh sẽ tự động xóa sau 5 giây...")
                await asyncio.sleep(5)
                await it.channel.delete()

        embed = discord.Embed(
            title=f"{Emojis.YIYITIM} support ticket",
            description=f"chào {user.mention}, cậu đang ở trong kênh hỗ trợ.\nnhân viên {staff_role.mention if staff_role else 'hệ thống'} sẽ phản hồi cậu tại đây.",
            color=0xf8bbd0
        )
        await channel.send(content=f"{user.mention} {staff_role.mention if staff_role else ''}", embed=embed, view=CloseButton())
        await interaction.followup.send(f"{Emojis.MATTRANG} đã tạo kênh hỗ trợ cho cậu tại {channel.mention}", ephemeral=True)

    async def _execute_verify_logic(self, interaction: discord.Interaction, member_role_id: str):
        """Xác thực người dùng (Security & Gatekeeping)"""
        await interaction.response.defer(ephemeral=True)
        role = interaction.guild.get_role(int(member_role_id)) if member_role_id.isdigit() else None

        if not role:
            return await interaction.followup.send(f"{Emojis.HOICHAM} lỗi hệ thống: không tìm thấy role xác thực.", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.followup.send(f"{Emojis.YIYITIM} cậu đã xác thực thành công từ trước rồi nhé!", ephemeral=True)

        # SECURITY: Check account age (Chống Clone)
        age = (discord.utils.utcnow() - interaction.user.created_at).days
        if age < 3:
            # Ghi log âm thầm cho admin check
            print(f"[SECURITY] User {interaction.user.id} verify với acc mới ({age} ngày).", flush=True)

        try:
            await interaction.user.add_roles(role)
            await interaction.followup.send(f"{Emojis.YIYITIM} **xác thực thành công!** chào mừng cậu đã gia nhập **{interaction.guild.name}**.", ephemeral=True)
        except:
            await interaction.followup.send(f"{Emojis.HOICHAM} yiyi không thể cấp role xác thực, hãy báo admin kiểm tra lại nhé!", ephemeral=True)

    # ----------------------------------------------
    # [THÊM MỚI] OMNI-INTERACTION EXTENSIONS
    # ----------------------------------------------

    async def _execute_menu_role_logic(self, interaction: discord.Interaction):
        """Xử lý chọn Role từ Menu thả xuống (Dropdown)"""
        await interaction.response.defer(ephemeral=True)
        values = interaction.data.get("values", [])
        if not values: return
        
        role_id = values[0]
        role = interaction.guild.get_role(int(role_id))
        if not role: return await interaction.followup.send(f"{Emojis.HOICHAM} Role không tồn tại.")

        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.followup.send(f"{Emojis.MATTRANG} đã gỡ role **{role.name}**.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"{Emojis.YIYITIM} đã cấp role **{role.name}** thành công!", ephemeral=True)
        except:
            await interaction.followup.send(f"{Emojis.HOICHAM} Yiyi không đủ quyền cấp role này.", ephemeral=True)

    async def _handle_extra_interactions(self, interaction: discord.Interaction, parts: list):
        """Xử lý các hệ lẻ: Gacha, Vote, Secret Message, Refresh, Dismiss"""
        itype = parts[2]
        data = parts[3] if len(parts) > 3 else "none"

        # 5.1. Secret Message (Chỉ người bấm thấy)
        if itype == "secret":
            # Giải nén Token (Gạch dưới -> Khoảng trắng)
            clean_msg = data.replace("_", " ")
            await interaction.response.send_message(f"{Emojis.YIYITIM} **Tin nhắn bí mật cho cậu:**\n> {clean_msg}", ephemeral=True)

        # 5.2. Gacha (Quay nhân phẩm)
        elif itype == "gacha":
            await interaction.response.defer(ephemeral=True)
            outcomes = ["Thần kỳ ✨", "May mắn 👍", "Bình thường 😐", "Đen đủi 💀", "Tuyệt vọng 🤡"]
            luck = random.choice(outcomes)
            await interaction.followup.send(f"{Emojis.MATTRANG} Kết quả nhân phẩm của {interaction.user.mention}: **{luck}**")

        # 5.3. Vote (Biểu quyết nhanh)
        elif itype == "vote":
            # Ghi nhận biểu quyết (Logic lưu trữ sẽ xử lý tại Phase sau nếu sếp cần đếm số)
            await interaction.response.send_message(f"{Emojis.YIYITIM} Cảm ơn cậu đã tham gia biểu quyết!", ephemeral=True)

        # 5.4. Dismiss (Dọn dẹp tin nhắn)
        elif itype == "dismiss":
            if interaction.user.guild_permissions.manage_messages:
                await interaction.message.delete()
            else:
                await interaction.response.send_message(f"{Emojis.HOICHAM} Cậu không có quyền dọn dẹp tin nhắn này!", ephemeral=True)

        # 5.5. Refresh (Cập nhật Realtime)
        elif itype == "refresh":
            await interaction.response.defer()
            # Tương tác này kích hoạt lại việc gửi Embed để cập nhật các biến số {timestamp}, {member_count}...
            await interaction.edit_original_response(content=f"{Emojis.YIYITIM} Đã làm mới trạng thái dữ liệu!")

async def setup(bot: commands.Bot):
    """nạp listener vào event loop của bot"""
    await bot.add_cog(ButtonListener(bot))
    print("[load] success: systems.button_listener (Phase 3 Full Omni-Interaction Brain)", flush=True)


