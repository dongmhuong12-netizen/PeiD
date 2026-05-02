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

# [BỔ SUNG PHASE 3] Hàm tạo View nút bấm từ dữ liệu lưu trữ
def create_embed_view(data):
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    view = discord.ui.View()
    for btn in buttons_data:
        if btn.get("type") == "link":
            view.add_item(discord.ui.Button(label=btn["label"], url=btn["url"]))
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
        # QUY TẮC 3S: Defer ngay lập tức - ephemeral=False để người khác có thể thấy banner đang thiết kế
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        
        # Validation chuẩn IT Pro
        if await load_embed(guild.id, name):
            # Nhóm 1a: Phản hồi Embed
            embed_exists = discord.Embed(
                title=f"{Emojis.MATTRANG} embed tên `{name}` đã tồn tại",
                description=f"nếu cậu không tìm thấy embed, hãy thử dùng `/p embed edit` để tìm lại nhé",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_exists)

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        # Khởi tạo bản ghi ban đầu
        # Nhóm 1b: Giữ nguyên logic/phản hồi lỗi
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            return await interaction.followup.send(f"phát sinh lỗi khi tạo embed `{error}`")

        # Nạp dữ liệu vừa tạo
        embed_data = await load_embed(guild.id, name)
        
        # [VÁ LỖI] Khởi tạo View (View sẽ tự đăng ký vào ACTIVE_EMBED_VIEWS để quản lý RAM)
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        # Nhóm 1c: Giữ nguyên văn phong thành công
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
        # IT Standard Defer
        await interaction.response.defer(ephemeral=False)
        
        data = await load_embed(interaction.guild.id, name)
        if not data:
            # Nhóm 1d: Phản hồi Embed Title & Description
            embed_none = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm...?",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`, xin hãy nhập lại lần nữa",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_none)

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        # [VÁ LỖI] Đăng ký View vào bộ nhớ được xử lý tự động trong EmbedUIView
        view = EmbedUIView(interaction.guild.id, name, data, timeout=600.0)
        embed = view.build_embed()

        # Nhóm 1e: Text thuần sửa cẩn thận
        msg = await interaction.followup.send(
            content=f" **yiyi** mang embed về rồi, xin hãy tiếp tục chỉnh sửa {Emojis.YIYITIM}", 
            embed=embed, 
            view=view
        )
        view.message = msg

    @app_commands.command(name="show", description="gửi embed vào channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):
        # Async fetch
        data = await load_embed(interaction.guild.id, name)
        if not data: 
            # Nhóm 2a: Split Title/Description
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé.",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn show bằng `/p embed edit`",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        # Nhóm 2b: Text thuần
        await interaction.response.send_message(f"{Emojis.MATTRANG} embed `{name}` gửi đi thành công", ephemeral=False)
        
        # [CẬP NHẬT] Kiểm tra và gắn nút bấm (nếu có) khi hiển thị
        view = create_embed_view(data)
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name, view=view)

    @app_commands.command(name="delete", description="xóa embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        # Await delete task
        await delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        # Nhóm 2c: Text thuần
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
        # Bảo tồn DNA log của cậu
        print("[load] success: commands.embed.embed_group", flush=True)
        
        # 2. Đăng ký lệnh /p image (Hệ thống CDN)
        if not any(c.name == "image" for c in p_cmd.commands):
            p_cmd.add_command(p_image_cmd)
            print("[load] success: commands.p.image (cdn engine)", flush=True)
    else:
        # IT Standard Error Log
        print("[error] không tìm thấy khung /p! hãy đảm bảo command /p đã được khởi tạo trước.", flush=True)


