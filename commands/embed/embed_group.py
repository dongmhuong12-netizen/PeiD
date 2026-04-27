
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

# =============================
# HELPERS (Bổ trợ) - GIỮ NGUYÊN 100% DNA CỦA NGUYỆT
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    # IT Pro: Luôn await các tác vụ I/O để tránh block event loop
    names = await get_all_embed_names(guild.id)
    return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]

def _cleanup_views(key: str):
    views = ACTIVE_EMBED_VIEWS.get(key)
    if not views: return
    for view in list(views):
        if hasattr(view, "message") and view.message:
            try: asyncio.create_task(view.message.delete())
            except: pass
        view.stop()
    ACTIVE_EMBED_VIEWS[key] = []

# =============================
# IMAGE COMMAND (BỔ SUNG VÀO HỆ LỆNH /P)
# =============================

@app_commands.command(name="image", description="Upload file to get permanent CDN link")
@app_commands.describe(file="Select the Image, GIF or Video file to get link")
async def p_image_cmd(interaction: discord.Interaction, file: discord.Attachment):
    """Lệnh /p image xử lý upload và tạo link CDN vĩnh viễn"""
    # Tư duy IT Pro: Defer ngay lập tức để tránh lỗi Interaction Failed khi xử lý file lớn
    await interaction.response.defer(ephemeral=True)
    # Gọi logic xử lý từ core engine (Chuyển tiếp interaction và client)
    await process_image_upload(interaction, file, interaction.client)

# =============================
# EMBED MODULE LOGIC (KHÔI PHỤC TOÀN BỘ CẤU TRÚC LỆNH)
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Hệ thống quản lý Embed chuyên sâu")

    @app_commands.command(name="create", description="Tạo Embed thiết kế mới")
    async def create(self, interaction: discord.Interaction, name: str):
        # QUY TẮC 3S: Defer ngay lập tức - ephemeral=False để người khác có thể thấy banner đang thiết kế
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        
        # Validation chuẩn IT Pro
        if await load_embed(guild.id, name):
            return await interaction.followup.send(f"❌ Embed `{name}` đã tồn tại. Dùng `/p embed edit` để sửa.")

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        # Khởi tạo bản ghi ban đầu
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            return await interaction.followup.send(f"❌ Lỗi: {error}")

        # Nạp dữ liệu vừa tạo
        embed_data = await load_embed(guild.id, name)
        
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        # CẬP NHẬT TEXT HƯỚNG DẪN: PHÙ HỢP VỚI CHẾ ĐỘ AUTO-SAVE
        msg = await interaction.followup.send(
            content=(
                f"Đã tạo embed với tên `{name}`\n\n"
                "Sử dụng các nút bên dưới để chỉnh sửa embed. **Hệ thống sẽ tự động lưu mọi thay đổi.**\n\n"
                "• Edit Information → Chỉnh sửa tiêu đề, mô tả và màu sắc\n"
                "• Edit Author → Chỉnh sửa thông tin tác giả\n"
                "• Edit Footer → Chỉnh sửa chân trang & timestamp\n"
                "• Set Image → Đặt ảnh hoặc GIF cho embed\n"
                "• Reaction Role → Thiết lập emoji và role để người dùng react nhận role\n\n"
                "• Cậu có thể sử dụng embed này để tạo tin nhắn chào mừng, rời đi, "
                "hoặc các banner hệ thống khi dùng lệnh `/p embed show`.\n"
                "• Để xóa embed này vĩnh viễn, hãy sử dụng lệnh `/p embed delete`.\n\n"
                "• Nếu có thắc mắc, dùng lệnh **/help** hoặc tham gia server hỗ trợ."
            ),
            embed=embed,
            view=view
        )
        
        view.message = msg
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="edit", description="Chỉnh sửa Embed hiện có")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str):
        # IT Standard Defer
        await interaction.response.defer(ephemeral=False)
        
        data = await load_embed(interaction.guild.id, name)
        if not data: return await interaction.followup.send(f"❌ Không tìm thấy `{name}`.")

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        view = EmbedUIView(interaction.guild.id, name, data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=f"📝 Bạn đang chỉnh sửa embed `{name}`. Mọi thay đổi sẽ được lưu tự động.", 
            embed=embed, 
            view=view
        )
        view.message = msg
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="show", description="Gửi Embed vào channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):
        # Async fetch
        data = await load_embed(interaction.guild.id, name)
        if not data: return await interaction.followup.send(f"❌ Không có `{name}` để show.", ephemeral=True)
        
        # IT Pro: Thông báo trạng thái gửi (ephemeral)
        await interaction.response.send_message(f"⌛ Đang gửi embed `{name}`...", ephemeral=True)
        
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name)

    @app_commands.command(name="delete", description="Xóa Embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        # Await delete task
        await delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        # Kết quả công khai
        await interaction.response.send_message(f"🗑️ Embed `{name}` đã được xoá vĩnh viễn.", ephemeral=False)

# =============================
# INJECTION (KHÔI PHỤC MẠCH ĐĂNG KÝ LỆNH CHUẨN)
# =============================

async def setup(bot: commands.Bot):
    # Truy xuất lệnh cha /p từ command tree toàn cục
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # 1. Khôi phục nhóm lệnh /p embed ...
        if not any(c.name == "embed" for c in p_cmd.commands):
            p_cmd.add_command(EmbedGroup())
            # Bảo tồn DNA log của cậu
            print("[LOAD] Success: commands.embed.embed_group", flush=True)
        
        # 2. Đăng ký lệnh /p image (Hệ thống CDN)
        if not any(c.name == "image" for c in p_cmd.commands):
            p_cmd.add_command(p_image_cmd)
            print("[LOAD] Success: commands.p.image (CDN Engine)", flush=True)
    else:
        # IT Standard Error Log
        print("[ERROR] Không tìm thấy khung /p! Hãy đảm bảo command /p đã được khởi tạo trước.", flush=True)

```
