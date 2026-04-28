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
        # QUY TẮC 3S: Defer ngay lập tức - ephemeral=False để người khác có thể thấy banner đang thiết kế
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        
        # Validation chuẩn IT Pro
        if await load_embed(guild.id, name):
            return await interaction.followup.send(f"embed `{name}` đã tồn tại, nếu cậu không tìm thấy embed, hãy dùng `/p embed edit` để tìm lại nhé")

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        # Khởi tạo bản ghi ban đầu
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            return await interaction.followup.send(f"phát sinh lỗi khi tạo embed `{error}`")

        # Nạp dữ liệu vừa tạo
        embed_data = await load_embed(guild.id, name)
        
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        # CẬP NHẬT TEXT HƯỚNG DẪN: PHÙ HỢP VỚI CHẾ ĐỘ AUTO-SAVE
        msg = await interaction.followup.send(
            content=(
                f"• đã tạo embed với tên `{name}`\n\n"
                "• sử dụng các nút bên dưới để chỉnh sửa embed\n\n"
                f"• cậu có thể sử dụng embed này để tạo tin nhắn tiếp tân (greet/leave - wellcome), tạo embed chúc mừng cho booster, các banner hệ thống khi dùng lệnh `/p embed show` hoặc setup pick role"
            ),
            embed=embed,
            view=view
        )
        
        view.message = msg
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="edit", description="chỉnh sửa embed hiện có")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str):
        # IT Standard Defer
        await interaction.response.defer(ephemeral=False)
        
        data = await load_embed(interaction.guild.id, name)
        if not data: return await interaction.followup.send(f"không tìm thấy embed có tên `{name}`, hãy nhập lại thử nhé")

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        view = EmbedUIView(interaction.guild.id, name, data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=f"tìm embed `{name}` thành công, hãy tiếp tục chỉnh sửa", 
            embed=embed, 
            view=view
        )
        view.message = msg
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="show", description="gửi embed vào channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):
        # Async fetch
        data = await load_embed(interaction.guild.id, name)
        if not data: 
            # PHẢN HỒI BẰNG EMBED MÀU f8bbd0 THEO YÊU CẦU
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé. yiyi không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn show bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        # IT Pro: Thông báo trạng thái gửi (ephemeral=False)
        await interaction.response.send_message(f"embed `{name}`gửi đi thành công", ephemeral=False)
        
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name)

    @app_commands.command(name="delete", description="xóa embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        # Await delete task
        await delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        # Kết quả công khai
        await interaction.response.send_message(f"embed `{name}` đã được xoá, có thể tạo embed mới bằng tên của embed này", ephemeral=False)

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
            print("[load] success: commands.embed.embed_group", flush=True)
        
        # 2. Đăng ký lệnh /p image (Hệ thống CDN)
        if not any(c.name == "image" for c in p_cmd.commands):
            p_cmd.add_command(p_image_cmd)
            print("[load] success: commands.p.image (cdn engine)", flush=True)
    else:
        # IT Standard Error Log
        print("[error] không tìm thấy khung /p! hãy đảm bảo command /p đã được khởi tạo trước.", flush=True)
