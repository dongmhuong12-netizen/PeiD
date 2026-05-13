import discord
from discord import app_commands
from discord.ext import commands
import re

# Nhập các lõi lưu trữ và engine biến số đã được nâng cấp Async
from core.identity_storage import save_identity, delete_identity, get_all_identity_names, load_identity
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER
# =============================

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    """
    [VÁ LỖI CHÍ MẠNG] Gợi ý tên vỏ thần tốc từ Cloud Atlas.
    Đảm bảo danh sách luôn hiện ra đầy đủ khi sếp gõ lệnh xóa/list.
    """
    guild = interaction.guild
    if not guild: return []
    try:
        # [KẾT NỐI MẠCH] Phải await để nạp danh sách từ MongoDB/RAM
        names = await get_all_identity_names(guild.id)
        return [
            app_commands.Choice(name=n, value=n) 
            for n in names if current.lower() in n.lower()
        ][:25]
    except: 
        return []

# =============================
# IDENTITY COMMAND GROUP
# =============================

class IdentityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="identity", description="quản lý danh tính giả (vỏ) cho webhook")

    # --- LỆNH THÊM VỎ (BẢN KIỂM ĐỊNH + PREVIEW BIẾN SỐ) ---
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
        # QUY TẮC 3S: Defer ngay lập tức để giữ mạch kết nối với Discord (Industrial Standard)
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        member = interaction.user

        # 1. KIỂM ĐỊNH LOẠI 3: MƯỢN XÁC (TARGET ID)
        if target_id:
            clean_id = re.sub(r'\D', '', str(target_id))
            if not clean_id:
                return await interaction.followup.send(f"{Emojis.HOICHAM} ID không hợp lệ, hãy nhập số hoặc mention người dùng.")
            
            try:
                # Fetch trực tiếp từ API Discord để lấy dữ liệu "sạch"
                target_user = await interaction.client.fetch_user(int(clean_id))
                display_name = target_user.display_name
                avatar_url = target_user.display_avatar.url
                target_id = clean_id
                ident_type = "target"
            except:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy người dùng có ID `{clean_id}`.")

        # 2. KIỂM ĐỊNH LOẠI 1 & 2: THỦ CÔNG/BIẾN SỐ
        else:
            if not display_name:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Cậu cần nhập 'Tên hiển thị' cho loại vỏ này.")
            
            if avatar_url and not avatar_url.startswith(("http://", "https://", "{")):
                return await interaction.followup.send(f"{Emojis.HOICHAM} Link ảnh phải bắt đầu bằng http/https hoặc biến số.")
            
            ident_type = "manual"

        # 3. [KẾT NỐI MẠCH] LƯU VÀO KHO (MONGODB SYNC)
        # Phải await để dữ liệu được khắc vào Cloud Atlas trước khi báo thành công
        success = await save_identity(
            guild_id=guild.id,
            name=id_name,
            display_name=display_name,
            avatar_url=avatar_url,
            target_id=target_id,
            ident_type=ident_type
        )

        if success:
            # --- LOGIC QUAN TRỌNG: DỊCH BIẾN SỐ ĐỂ PREVIEW ---
            preview_name = apply_variables(display_name, guild, member)
            
            if ident_type == "target":
                info_detail = f"Mượn xác: **{display_name}**"
            else:
                if "{" in display_name:
                    info_detail = f"Mã lưu: `{display_name}`\n> 👁️ Xem trước: **{preview_name}**"
                else:
                    info_detail = f"Tên hiển thị: **{display_name}**"

            await interaction.followup.send(
                f"{Emojis.YIYITIM} **Đã lưu danh tính thành công!**\n"
                f"> 🆔 Tên gợi nhớ: `{id_name}`\n"
                f"> 🎭 Thông tin: {info_detail}"
            )

    # --- LỆNH XÓA VỎ ---
    @app_commands.command(name="delete", description="xóa một 'vỏ' khỏi kho lưu trữ")
    @app_commands.autocomplete(name=identity_autocomplete)
    async def delete_id(self, interaction: discord.Interaction, name: str):
        # Industrial Defer
        await interaction.response.defer(ephemeral=True)
        
        # [KẾT NỐI MẠCH] Await xóa sạch cả RAM lẫn Cloud Atlas
        success = await delete_identity(interaction.guild.id, name)
        
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} Đã xóa sạch dấu vết của vỏ `{name}`!")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy vỏ nào tên `{name}`.")

    # --- LỆNH LIỆT KÊ DANH SÁCH ---
    @app_commands.command(name="list", description="xem danh sách các 'vỏ' đang có ở server này")
    async def list_identities(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # [KẾT NỐI MẠCH] Truy vấn toàn bộ danh sách từ Cloud/RAM
        names = await get_all_identity_names(interaction.guild.id)
        
        if not names:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Server mình chưa có cái 'vỏ' nào cả.")

        embed = discord.Embed(
            title=f"{Emojis.YIYITIM} Kho Danh Tính - {interaction.guild.name}",
            description="Danh sách các 'vỏ' khả dụng",
            color=0xf8bbd0
        )

        for n in names:
            # [KẾT NỐI MẠCH] Await nạp dữ liệu chi tiết từng vỏ
            data = await load_identity(interaction.guild.id, n)
            if not data: continue
            
            raw_dn = data.get("display_name", "Unknown")
            preview_dn = apply_variables(raw_dn, interaction.guild, interaction.user)
            
            v_type = "🎯 Mượn xác" if data.get("type") == "target" else "🎭 Tùy chỉnh"
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
        existing = next((c for c in p_cmd.commands if c.name == "identity"), None)
        if existing: p_cmd.remove_command("identity")
        
        p_cmd.add_command(IdentityGroup())
        print("[load] success: identity_group (Preview & Variable Sync Edition)", flush=True)
