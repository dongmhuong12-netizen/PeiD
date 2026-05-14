import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed
from systems.embed_system import EmbedSystem

# IMPORT ENGINE IMAGE MỚI (Xử lý CDN vĩnh viễn)
from core.image_engine import process_image_upload
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# =============================
# HELPERS (Bổ trợ) - GIỮ NGUYÊN 100% DNA CỦA NGUYỆT
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    [VÁ LỖI CHÍ MẠNG] 
    Autocomplete thần tốc chống lỗi 404 Unknown Interaction.
    Đảm bảo danh sách luôn hiện ra đầy đủ khi sếp gõ lệnh.
    """
    guild = interaction.guild
    if not guild: return []
    
    try:
        # [KẾT NỐI MẠCH] Phải await vì storage giờ đã lên Cloud Atlas
        names = await get_all_embed_names(guild.id)
        
        # Logic lọc tên của sếp (Giữ nguyên văn phong logic)
        choices = [
            app_commands.Choice(name=name, value=name) 
            for name in names if current.lower() in name.lower()
        ][:25]
        
        return choices
    except Exception:
        # IT Pro: Nếu interaction đã chết hoặc lag, trả về list rỗng thay vì nổ lỗi 404
        return []

def _cleanup_views(key: str):
    views = ACTIVE_EMBED_VIEWS.get(key)
    if not views: return
    for view in list(views):
        if hasattr(view, "message") and view.message:
            try: asyncio.create_task(view.message.delete())
            except: pass
        view.stop()
    ACTIVE_EMBED_VIEWS[key] = []

# [BỔ SUNG PHASE 3] Hàm tạo View nút bấm từ dữ liệu lưu trữ
def create_embed_view(data):
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    # [INDUSTRIAL] timeout=None để nút luôn sống vĩnh viễn trên kênh được show
    view = discord.ui.View(timeout=None)
    
    # Map màu sắc nút chuẩn Industrial
    style_map = {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
    }

    for btn in buttons_data:
        b_type = btn.get("type")
        
        # 1. MẠCH NÚT LINK (Chuyển hướng)
        if b_type == "link":
            view.add_item(discord.ui.Button(
                label=btn.get("label"), 
                url=btn.get("url"), 
                emoji=btn.get("emoji")
            ))
            
        # 2. MẠCH NÚT HỆ THỐNG (Multi-IT: Chấp nhận mọi loại Button tương tác)
        elif b_type == "button":
            # Tự động nhận diện Style, Label và CustomID để kích hoạt hệ thống tương ứng
            view.add_item(discord.ui.Button(
                style=style_map.get(btn.get("style", "secondary").lower(), discord.ButtonStyle.secondary),
                label=btn.get("label"),
                custom_id=btn.get("custom_id"),
                emoji=btn.get("emoji")
            ))
            
    return view

# =============================
# IMAGE COMMAND (BỔ SUNG VÀO HỆ LỆNH /P)
# =============================

@app_commands.command(name="image", description="upload file to get permanent cdn link")
@app_commands.describe(file="select the image, gif or video file to get link")
async def p_image_cmd(interaction: discord.Interaction, file: discord.Attachment):
    """Lệnh /p image xử lý upload và tạo link CDN vĩnh viễn"""
    # Tư duy IT Pro: Defer ngay lập tức để tránh lỗi Interaction Failed khi xử lý file lớn
    await interaction.response.defer(ephemeral=False)
    # Gọi logic xử lý từ core engine (Chuyển tiếp interaction và client)
    await process_image_upload(interaction, file, interaction.client)

# =============================
# EMBED MODULE LOGIC (KHÔI PHỤC TOÀN BỘ CẤU TRÚC LỆNH)
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="hệ thống quản lý embed chuyên sâu")

    @app_commands.command(name="create", description="tạo embed thiết kế mới")
    async def create(self, interaction: discord.Interaction, name: str):
        # QUY TẮC 3S: Defer ngay lập tức để giữ mạch kết nối với Discord (Industrial Standard)
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        
        # [KẾT NỐI MẠCH] Load từ Cloud phải dùng await
        if await load_embed(guild.id, name):
            embed_exists = discord.Embed(
                title=f"{Emojis.MATTRANG} embed tên `{name}` đã tồn tại",
                description=f"nếu cậu không tìm thấy embed, hãy thử dùng `/p embed edit` để tìm lại nhé",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_exists)

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        # [KẾT NỐI MẠCH] Logic tạo bản ghi ban đầu trên Cloud
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            return await interaction.followup.send(f"phát sinh lỗi khi tạo embed `{error}`")

        # Nạp dữ liệu vừa tạo từ Cloud
        embed_data = await load_embed(guild.id, name)
        
        # [VÁ LỖI] Khởi tạo View (View sẽ tự đăng ký vào ACTIVE_EMBED_VIEWS để quản lý RAM)
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=(
                f"• đã tạo embed với tên `{name}`\n"
                "• sử dụng các nút bên dưới để chỉnh sửa embed\n"
                f"• cậu có thể sử dụng embed này để tạo tin nhắn tiếp tân (greet/leave - wellcome), tạo embed chúc mừng cho booster, các banner hệ thống khi dùng lệnh `/p embed show` hoặc setup pick role"
            ),
            embed=embed,
            view=view
        )
        
        view.message = msg

    @app_commands.command(name="edit", description="chỉnh sửa embed hiện có")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str):
        # IT Standard Defer: Tránh lỗi "Interaction Failed" khi Cloud phản hồi chậm
        await interaction.response.defer(ephemeral=False)
        
        # [KẾT NỐI MẠCH] Await để nạp linh hồn embed từ MongoDB
        data = await load_embed(interaction.guild.id, name)
        if not data:
            embed_none = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm...?",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`, xin hãy nhập lại lần nữa",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_none)

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        # Khởi tạo UI Editor
        view = EmbedUIView(interaction.guild.id, name, data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=f" **yiyi** mang embed về rồi, xin hãy tiếp tục chỉnh sửa {Emojis.YIYITIM}", 
            embed=embed, 
            view=view
        )
        view.message = msg

    @app_commands.command(name="show", description="gửi embed vào channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):
        # [KẾT NỐI MẠCH] Nạp dữ liệu từ Cloud Atlas
        data = await load_embed(interaction.guild.id, name)
        if not data: 
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé.",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn show bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        # Phản hồi nhẹ nhàng cho Admin
        await interaction.response.send_message(f"{Emojis.MATTRANG} embed `{name}` gửi đi thành công", ephemeral=True)
        
        # Giữ nguyên DNA: Tạo View nút bấm linh hoạt cho toàn bộ hệ thống
        view = create_embed_view(data)
        
        # [THỰC THI] Gửi embed thông qua Engine vạn năng
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name, view=view)

    @app_commands.command(name="delete", description="xóa embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        # [KẾT NỐI MẠCH] Await để lệnh xóa thực thi xong trên Cloud mới báo thành công
        await delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        
        await interaction.response.send_message(f"{Emojis.MATTRANG} embed `{name}` đã được xoá thành công. có thể tạo lại embed mới bằng tên của embed này", ephemeral=False)

# =============================
# INJECTION (KHÔI PHỤC MẠCH ĐĂNG KÝ LỆNH CHUẨN)
# =============================

async def setup(bot: commands.Bot):
    # Truy xuất lệnh cha /p từ command tree toàn cục
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # [CẬP NHẬT] Xóa group cũ trước khi nạp để tránh lỗi lệnh ma khi reload
        existing_embed = next((c for c in p_cmd.commands if c.name == "embed"), None)
        if existing_embed: p_cmd.remove_command("embed")
        
        # 1. Khôi phục nhóm lệnh /p embed ...
        p_cmd.add_command(EmbedGroup())
        print("[load] success: commands.embed.embed_group", flush=True)
        
        # 2. Đăng ký lệnh /p image (Hệ thống CDN)
        if not any(c.name == "image" for c in p_cmd.commands):
            p_cmd.add_command(p_image_cmd)
            print("[load] success: commands.p.image (cdn engine)", flush=True)
    else:
        print("[error] không tìm thấy khung /p! hãy đảm bảo command /p đã được khởi tạo trước.", flush=True)
