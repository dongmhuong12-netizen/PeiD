import discord
from discord import app_commands
from discord.ext import commands
import re
import asyncio

# Nhập các lõi lưu trữ và engine biến số đã được nâng cấp Async
from core.identity_storage import save_identity, delete_identity, get_all_identity_names, load_identity
from core.embed_storage import load_embed, get_all_embed_names # [CẤY MỚI] Để phục vụ lệnh send
from core.variable_engine import apply_variables
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPERS
# =============================

async def identity_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_identity_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except: return []

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """[CẤY MỚI] Gợi ý tên embed để sếp chọn khi gửi bằng danh tính giả"""
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
    except: return []

# =============================
# MULTI-IT VIEW GENERATOR (MỞ CỬA CHO TẤT CẢ HỆ NÚT)
# =============================

def create_embed_view(data):
    """Hàm tạo View nút bấm vạn năng - Đón nhận mọi loại Button tương tác"""
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    view = discord.ui.View(timeout=None)
    style_map = {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
    }

    for btn in buttons_data:
        b_type = btn.get("type")
        if b_type == "link":
            view.add_item(discord.ui.Button(
                label=btn.get("label"), 
                url=btn.get("url"), 
                emoji=btn.get("emoji")
            ))
        elif b_type == "button":
            view.add_item(discord.ui.Button(
                style=style_map.get(btn.get("style", "secondary").lower(), discord.ButtonStyle.secondary),
                label=btn.get("label"),
                custom_id=btn.get("custom_id"),
                emoji=btn.get("emoji")
            ))
    return view

# =============================
# IDENTITY COMMAND GROUP
# =============================

class IdentityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="identity", description="quản lý danh tính giả (vỏ) cho webhook")

    # --- LỆNH 1: GỬI EMED GIẢ DANH (IDENTITY SEND) ---
    @app_commands.command(name="send", description="gửi embed dưới danh nghĩa một 'vỏ' (Identity)")
    @app_commands.describe(
        id_name="Tên vỏ muốn sử dụng",
        embed_name="Tên embed muốn gửi",
        channel="Kênh muốn gửi đến (mặc định là kênh hiện tại)"
    )
    @app_commands.autocomplete(id_name=identity_autocomplete, embed_name=embed_name_autocomplete)
    async def send_with_identity(
        self, 
        interaction: discord.Interaction, 
        id_name: str, 
        embed_name: str, 
        channel: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        target_channel = channel or interaction.channel

        # 1. Nạp linh hồn (Identity) và xác (Embed)
        id_data = await load_identity(guild.id, id_name)
        embed_data = await load_embed(guild.id, embed_name)

        if not id_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy vỏ `{id_name}`.")
        if not embed_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy embed `{embed_name}`.")

        # 2. Xử lý danh tính qua engine biến số
        final_name = apply_variables(id_data.get("display_name", "Yiyi Identity"), guild, interaction.user)
        final_avatar = apply_variables(id_data.get("avatar_url"), guild, interaction.user)

        # 3. Chuẩn bị View Multi-IT (Full nút Ticket/Form/Link)
        view = create_embed_view(embed_data)
        
        # 4. Mạch Webhook Industrial
        try:
            # Tìm webhook của Yiyi hoặc tạo mới nếu chưa có
            webhooks = await target_channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Yiyi-Identity")
            if not webhook:
                webhook = await target_channel.create_webhook(name="Yiyi-Identity")

            # Xây dựng Embed đối tượng từ data
            # Lưu ý: Vì gửi qua Webhook nên phải chuyển dict data thành discord.Embed
            # (Giả định sếp đã có hàm build_embed hoặc dùng cách nạp dict trực tiếp)
            from core.embed_ui import EmbedUIView # Nạp nhẹ view để mượn hàm build
            temp_view = EmbedUIView(guild.id, embed_name, embed_data)
            final_embed = temp_view.build_embed()

            # THỰC THI GỬI GIẢ DANH
            await webhook.send(
                username=final_name,
                avatar_url=final_avatar,
                embed=final_embed,
                view=view
            )
            await interaction.followup.send(f"{Emojis.MATTRANG} Đã gửi embed `{embed_name}` dưới danh tính `{id_name}` thành công!")
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} Lỗi gửi Webhook: `{str(e)}` - Hãy kiểm tra quyền của Yiyi nhé.")

    # --- LỆNH 2: THÊM VỎ ---
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
            clean_id = re.sub(r'\D', '', str(target_id))
            if not clean_id:
                return await interaction.followup.send(f"{Emojis.HOICHAM} ID không hợp lệ.")
            try:
                target_user = await interaction.client.fetch_user(int(clean_id))
                display_name = target_user.display_name
                avatar_url = target_user.display_avatar.url
                target_id = clean_id
                ident_type = "target"
            except:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy người dùng `{clean_id}`.")
        else:
            if not display_name:
                return await interaction.followup.send(f"{Emojis.HOICHAM} Cậu cần nhập 'Tên hiển thị'.")
            if avatar_url and not avatar_url.startswith(("http://", "https://", "{")):
                return await interaction.followup.send(f"{Emojis.HOICHAM} Link ảnh không hợp lệ.")
            ident_type = "manual"

        success = await save_identity(
            guild_id=guild.id, name=id_name, display_name=display_name,
            avatar_url=avatar_url, target_id=target_id, ident_type=ident_type
        )

        if success:
            preview_name = apply_variables(display_name, guild, member)
            info_detail = f"Mượn xác: **{display_name}**" if ident_type == "target" else f"Tên hiển thị: **{display_name}**"
            await interaction.followup.send(f"{Emojis.YIYITIM} **Đã lưu danh tính thành công!**\n> 🆔 Tên gợi nhớ: `{id_name}`\n> 🎭 Thông tin: {info_detail}")

    # --- LỆNH 3: XÓA VỎ ---
    @app_commands.command(name="delete", description="xóa một 'vỏ' khỏi kho lưu trữ")
    @app_commands.autocomplete(name=identity_autocomplete)
    async def delete_id(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        success = await delete_identity(interaction.guild.id, name)
        if success:
            await interaction.followup.send(f"{Emojis.MATTRANG} Đã xóa sạch dấu vết của vỏ `{name}`!")
        else:
            await interaction.followup.send(f"{Emojis.HOICHAM} Không tìm thấy vỏ nào tên `{name}`.")

    # --- LỆNH 4: LIỆT KÊ DANH SÁCH ---
    @app_commands.command(name="list", description="xem danh sách các 'vỏ' đang có ở server này")
    async def list_identities(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        names = await get_all_identity_names(interaction.guild.id)
        if not names:
            return await interaction.followup.send(f"{Emojis.HOICHAM} Server mình chưa có cái 'vỏ' nào cả.")

        embed = discord.Embed(title=f"{Emojis.YIYITIM} Kho Danh Tính - {interaction.guild.name}", color=0xf8bbd0)
        for n in names:
            data = await load_identity(interaction.guild.id, n)
            if not data: continue
            raw_dn = data.get("display_name", "Unknown")
            preview_dn = apply_variables(raw_dn, interaction.guild, interaction.user)
            v_type = "🎯 Mượn xác" if data.get("type") == "target" else "🎭 Tùy chỉnh"
            embed.add_field(name=f"🆔 `{n}`", value=f"Loại: {v_type}\nHiển thị: **{preview_dn}**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "identity"), None)
        if existing: p_cmd.remove_command("identity")
        p_cmd.add_command(IdentityGroup())
        print("[load] success: identity_group (Multi-IT Send Edition)", flush=True)
