import discord
from discord import app_commands
from discord.ext import commands
import re
from core.identity_storage import save_identity, delete_identity, get_all_identity_names, load_identity
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER
# =============================

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    """Gợi ý tên vỏ để xóa hoặc quản lý"""
    guild = interaction.guild
    if not guild: return []
    names = await get_all_identity_names(guild.id)
    return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]

# =============================
# IDENTITY COMMAND GROUP
# =============================

class IdentityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="identity", description="quản lý danh tính giả (vỏ) cho webhook")

    # --- LỆNH THÊM VỎ (BẢN KIỂM ĐỊNH MAX PING) ---
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
        
        # 1. KIỂM ĐỊNH LOẠI 3: MƯỢN XÁC (ID)
        if target_id:
            # Gọt vỏ ID: Loại bỏ <@! >, chỉ lấy dãy số
            clean_id = re.sub(r'\D', '', str(target_id))
            if not clean_id:
                return await interaction.followup.send(f"{Emojis.HOICHAM} ID không hợp lệ, hãy nhập số hoặc mention người dùng.")
            
            try:
                # IT Pro: Truy vấn trực tiếp Discord API để xác thực ID
                target_user = await interaction.client.fetch_user(int(clean_id))
                
                # Tự động gán info từ ID để đảm bảo tính chính xác
                display_name = target_user.display_name
                avatar_url = target_user.display_avatar.url
                target_id = clean_id
                ident_type = "target"
                
            except discord.NotFound:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy người dùng nào có ID `{clean_id}` trên Discord!")
            except Exception as e:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi khi xác thực ID: `{str(e)}`")

        # 2. KIỂM ĐỊNH LOẠI 1 & 2: THỦ CÔNG/BIẾN SỐ
        else:
            if not display_name:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Cậu cần nhập 'Tên hiển thị' cho loại vỏ thủ công này.")
            
            # Check nhanh định dạng URL (tránh dán rác vào DB)
            if avatar_url and not avatar_url.startswith(("http://", "https://", "{")):
                return await interaction.followup.send(f"{Emojis.HOICHAM} Link ảnh không hợp lệ (phải bắt đầu bằng http/https hoặc biến số).")
            
            ident_type = "manual"

        # 3. LƯU VÀO KHO SAU KHI ĐÃ SẠCH DỮ LIỆU
        success = await save_identity(
            guild_id=interaction.guild.id,
            name=id_name,
            display_name=display_name,
            avatar_url=avatar_url,
            target_id=target_id,
            ident_type=ident_type
        )

        if success:
            detail = f"Mượn xác của: **{display_name}**" if ident_type == "target" else f"Tên hiển thị: `{display_name}`"
            await interaction.followup.send(
                f"{Emojis.YIYITIM} **Đã lưu danh tính thành công!**\n"
                f"> 🆔 Tên gợi nhớ: `{id_name}`\n"
                f"> 🎭 Thông tin: {detail}"
            )

    # --- LỆNH XÓA VỎ ---
    @app_commands.command(name="delete", description="xóa một 'vỏ' khỏi kho lưu trữ")
    @app_commands.autocomplete(name=identity_autocomplete)
    async def delete_id(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        
        success = await delete_identity(interaction.guild.id, name)
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} Đã xóa sạch dấu vết của vỏ `{name}`!")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} yiyi không thấy vỏ nào tên `{name}` để xóa cả.")

    # --- LỆNH LIỆT KÊ DANH SÁCH ---
    @app_commands.command(name="list", description="xem danh sách các 'vỏ' đang có ở server này")
    async def list_identities(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        names = await get_all_identity_names(interaction.guild.id)
        if not names:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Server mình chưa có cái 'vỏ' nào cả.")

        embed = discord.Embed(
            title=f"{Emojis.YIYITIM} Kho Danh Tính - {interaction.guild.name}",
            description="Danh sách các 'vỏ' khả dụng cho `/p embed send`",
            color=0x2b2d31
        )

        for n in names:
            data = await load_identity(interaction.guild.id, n)
            v_type = "🎯 Mượn xác" if data.get("type") == "target" else "🎭 Tùy chỉnh"
            embed.add_field(name=f"🆔 `{n}`", value=f"Loại: {v_type}", inline=True)

        await interaction.followup.send(embed=embed)

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn dẹp bản cũ nếu có để nạp bản kiểm định mới
        existing = next((c for c in p_cmd.commands if c.name == "identity"), None)
        if existing: p_cmd.remove_command("identity")
        
        p_cmd.add_command(IdentityGroup())
        print("[load] success: identity_group (Fail-Fast Verification Edition)", flush=True)
