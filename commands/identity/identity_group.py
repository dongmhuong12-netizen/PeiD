import discord
from discord import app_commands
from discord.ext import commands
import re
import asyncio

# Nhập các lõi lưu trữ và engine biến số đã được nâng cấp Async
from core.identity_storage import save_identity, delete_identity, get_all_identity_names, load_identity
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPERS
# =============================

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên danh tính để sếp thao tác nhanh"""
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_identity_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except: return []

# =============================
# IDENTITY COMMAND GROUP
# =============================

class IdentityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="identity", description="quản lý danh tính giả (vỏ) cho webhook")

    # --- LỆNH 1: THÊM VỎ ---
    @app_commands.command(name="add", description="tạo một 'vỏ' danh tính mới với kiểm định dữ liệu")
    @app_commands.describe(
        id_name="tên gợi nhớ của vỏ (vd: admin_vibe)",
        display_name="tên hiển thị trên webhook (có thể dùng biến {user_name})",
        avatar_url="link ảnh đại diện (có thể dùng biến {user_avatar})",
        target_id="ID người dùng muốn mượn xác (nếu dùng, Yiyi sẽ tự lấy tên/ảnh của họ)"
    )
    async def add_identity(
        self, 
        interaction: discord.Interaction, 
        id_name: str, 
        display_name: str = None, 
        avatar_url: str = None, 
        target_id: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        if target_id:
            # Tối ưu: Lọc sạch ký tự lạ khỏi ID
            clean_id = re.sub(r'\D', '', str(target_id))
            if not clean_id:
                return await interaction.followup.send(f"{Emojis.HOICHAM} id không hợp hệ, hãy thử nhập lại nhé.")
            try:
                target_user = await interaction.client.fetch_user(int(clean_id))
                display_name = target_user.display_name
                avatar_url = target_user.display_avatar.url
                target_id = clean_id
                ident_type = "target"
            except:
                return await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không tìm thấy người dùng `{clean_id}`.")
        else:
            if not display_name:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Cậu cần nhập 'Tên hiển thị' nhé.")
            if avatar_url and not avatar_url.startswith(("http://", "https://", "{")):
                return await interaction.followup.send(f"{Emojis.HOICHAM} Link ảnh có vẻ không đúng định dạng rồi.")
            ident_type = "manual"

        # Lưu vào kho lưu trữ
        success = await save_identity(
            guild_id=guild.id, name=id_name, display_name=display_name,
            avatar_url=avatar_url, target_id=target_id, ident_type=ident_type
        )

        if success:
            info_detail = f"Mượn xác: **{display_name}**" if ident_type == "target" else f"Tên hiển thị: **{display_name}**"
            await interaction.followup.send(
                f"{Emojis.BUOMA} **Đã lưu danh tính thành công!**\n"
                f"> 🆔 Tên gợi nhớ: `{id_name}`\n"
                f"> 🎭 Thông tin: {info_detail}"
            )

    # --- LỆNH 2: XÓA VỎ ---
    @app_commands.command(name="delete", description="xóa một 'vỏ' khỏi kho lưu trữ")
    @app_commands.autocomplete(name=identity_autocomplete)
    async def delete_id(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        
        success = await delete_identity(interaction.guild.id, name)
        if success:
            await interaction.followup.send(f"{Emojis.BUOMA} xoá vỏ `{name}` thành công.")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không tìm thấy vỏ nào có tên `{name}`. hãy thử nhập lại hoặc kiểm tra tên vỏ bằng `/p identity list`.")

    # --- LỆNH 3: LIỆT KÊ DANH SÁCH ---
    @app_commands.command(name="list", description="xem danh sách các 'vỏ' đang có ở server này")
    async def list_identities(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        names = await get_all_identity_names(interaction.guild.id)
        if not names:
            return await interaction.followup.send(f"{Emojis.HOICHAM} máy chủ này hiện chưa có `vỏ`.")

        embed = discord.Embed(
            title=f"{Emojis.BUOMA} Kho Danh Tính - {interaction.guild.name}", 
            color=0xe6e2dd
        )
        
        for n in names:
            data = await load_identity(interaction.guild.id, n)
            if not data: continue
            
            raw_dn = data.get("display_name", "Không tên")
            # Dịch biến số để sếp thấy trước kết quả hiển thị
            preview_dn = apply_variables(raw_dn, interaction.guild, interaction.user)
            v_type = "🎯 Mượn xác" if data.get("ident_type") == "target" else "🎭 Tùy chỉnh"
            
            embed.add_field(
                name=f"🆔 `{n}`", 
                value=f"Loại: {v_type}\nHiển thị: **{preview_dn}**", 
                inline=True
            )
            
        await interaction.followup.send(embed=embed)

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn dẹp để đảm bảo không bị trùng lặp nhóm lệnh
        existing = next((c for c in p_cmd.commands if c.name == "identity"), None)
        if existing: p_cmd.remove_command("identity")
        
        p_cmd.add_command(IdentityGroup())
        print("[load] success: identity_group (Clean Industrial Edition)", flush=True)
