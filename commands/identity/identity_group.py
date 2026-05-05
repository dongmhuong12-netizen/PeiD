import discord
from discord import app_commands
from discord.ext import commands
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

    # --- LỆNH THÊM VỎ (Hỗ trợ cả 3 loại) ---
    @app_commands.command(name="add", description="tạo một 'vỏ' danh tính mới")
    @app_commands.describe(
        id_name="tên gợi nhớ của vỏ (vd: admin_vibe)",
        display_name="tên hiển thị trên webhook (có thể dùng biến {user_name})",
        avatar_url="link ảnh đại diện (có thể dùng biến {user_avatar})",
        target_id="ID của người muốn mượn xác (nếu dùng loại này, bỏ qua 2 ô trên)"
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
        
        # Xác định loại vỏ dựa trên dữ liệu nhập vào
        ident_type = "target" if target_id else "manual"
        
        if ident_type == "target" and not str(target_id).isdigit():
            return await interaction.followup.send(f"{Emojis.HOICHAM} ID người dùng phải là một dãy số cậu nhé!")
            
        if ident_type == "manual" and not display_name:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Cậu cần nhập ít nhất là 'Tên hiển thị' cho loại vỏ này.")

        success = await save_identity(
            guild_id=interaction.guild.id,
            name=id_name,
            display_name=display_name,
            avatar_url=avatar_url,
            target_id=target_id,
            ident_type=ident_type
        )

        if success:
            msg = f"Đã lưu vỏ mượn xác ID `{target_id}`" if ident_type == "target" else f"Đã lưu vỏ `{id_name}`"
            await interaction.followup.send(f"{Emojis.YIYITIM} {msg} thành công rồi nè!")

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
            return await interaction.followup.send(f"{Emojis.HOICHAM} Server mình chưa có cái 'vỏ' nào cả, cậu tạo đi!")

        embed = discord.Embed(
            title=f"{Emojis.YIYITIM} Kho Danh Tính - {interaction.guild.name}",
            description="Dưới đây là các 'vỏ' cậu có thể dùng với lệnh `/p embed send`",
            color=0x2b2d31
        )

        for n in names:
            data = await load_identity(interaction.guild.id, n)
            v_type = "🎯 Mượn xác (ID)" if data.get("type") == "target" else "🎭 Tự chế/Biến số"
            embed.add_field(name=f"🆔 `{n}`", value=f"Loại: {v_type}", inline=True)

        await interaction.followup.send(embed=embed)

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Tiêm group identity vào dưới lệnh /p
        p_cmd.add_command(IdentityGroup())
        print("[load] success: identity_group (Admin Management Tools)", flush=True)
