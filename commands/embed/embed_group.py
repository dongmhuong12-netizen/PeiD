import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed

# =============================
# HELPERS (Bổ trợ)
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    names = get_all_embed_names(guild.id)
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
# EMBED MODULE LOGIC
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Hệ thống quản lý Embed chuyên sâu")

    @app_commands.command(name="create", description="Tạo Embed thiết kế mới")
    async def create(self, interaction: discord.Interaction, name: str):
        # QUY TẮC 3S: Câu giờ ngay lập tức
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if load_embed(guild.id, name):
            return await interaction.followup.send(f"❌ Embed `{name}` đã tồn tại. Dùng `/p embed edit` để sửa.")

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        embed_data = {
            "title": "Embed Mới", 
            "description": "Dùng các nút bên dưới để chỉnh sửa.", 
            "color": 0x5865F2
        }
        
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        # KHÔI PHỤC TOÀN BỘ TEXT HƯỚNG DẪN CỦA NGUYỆT
        msg = await interaction.followup.send(
            content=(
                f"Đã tạo embed với tên `{name}`\n\n"
                "Sử dụng các nút bên dưới để chỉnh sửa embed.\n\n"
                "• Edit Title → Chỉnh sửa tiêu đề\n"
                "• Edit Description → Chỉnh sửa mô tả\n"
                "• Set Image → Đặt ảnh cho embed\n"
                "• Edit Color → Đổi màu (mã hex)\n"
                "• Reaction Role → Thiết lập emoji và role để người dùng react nhận role\n"
                "• Save Embed → Lưu embed\n"
                "• Delete Embed → Xoá embed vĩnh viễn\n\n"
                "• Bạn có thể sử dụng embed này để tạo tin nhắn chào mừng, rời đi, "
                "hoặc các banner hệ thống khi dùng lệnh `/p embed show`.\n\n"
                "• Lưu ý: hãy Save sau khi chỉnh sửa. Nếu không embed sẽ không được lưu lại, "
                "hoặc sẽ bị coi là không tồn tại nếu chưa từng Save.\n"
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
        await interaction.response.defer(ephemeral=True)
        data = load_embed(interaction.guild.id, name)
        if not data: return await interaction.followup.send(f"❌ Không tìm thấy `{name}`.")

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        view = EmbedUIView(interaction.guild.id, name, data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=f"📝 Bạn đang chỉnh sửa embed `{name}`.", 
            embed=embed, 
            view=view
        )
        view.message = msg
        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="show", description="Gửi Embed vào channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):
        data = load_embed(interaction.guild.id, name)
        if not data: return await interaction.followup.send(f"❌ Không có `{name}` để show.", ephemeral=True)
        
        # Phản hồi nhẹ để tránh lỗi 3s của lệnh gốc
        await interaction.response.send_message(f"⌛ Đang gửi embed `{name}`...", ephemeral=True)
        
        # Gửi embed thật (Hàm này đã được fix ở state.py để lưu ID bền vững)
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name)

    @app_commands.command(name="delete", description="Xóa Embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        await interaction.response.send_message(f"🗑️ Embed `{name}` đã được xoá vĩnh viễn.", ephemeral=True)

# =============================
# INJECTION (TIÊM LỆNH VÀO KHUNG)
# =============================

async def setup(bot: commands.Bot):
    # Tìm lệnh /p đã được tạo ở root.py
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Kiểm tra tránh nạp chồng lệnh
        if not any(c.name == "embed" for c in p_cmd.commands):
            p_cmd.add_command(EmbedGroup())
            print("[LOAD] Success: commands.embed.embed_group (Injected into /p)", flush=True)
    else:
        print("[ERROR] Không tìm thấy khung /p! Kiểm tra thứ tự nạp trong main.py", flush=True)
