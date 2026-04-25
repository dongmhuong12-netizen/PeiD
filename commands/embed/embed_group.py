import discord
from discord import app_commands
from discord.ext import commands
import asyncio

# Import hệ thống đã được Async hóa
from systems.embed_system import EmbedSystem
from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed

# =============================
# HELPERS (Đã Async hóa)
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    # BẮT BUỘC AWAIT: Lấy danh sách tên từ Storage
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
# EMBED MODULE LOGIC
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Hệ thống quản lý Embed chuyên sâu")

    @app_commands.command(name="create", description="Tạo Embed thiết kế mới")
    async def create(self, interaction: discord.Interaction, name: str):
        # QUY TẮC 3S: Câu giờ ngay lập tức để tránh Timeout
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild

        # SỬ DỤNG HỆ THỐNG ĐÃ FIX: Gọi EmbedSystem để check Regex, Limit và Save mặc định
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            msg = "Lỗi không xác định."
            if error == "EXISTS": msg = f"Embed `{name}` đã tồn tại. Hãy dùng `/p embed edit`."
            elif error == "INVALID_NAME": msg = "Tên không hợp lệ (Chỉ dùng chữ, số, dấu cách, gạch ngang)."
            elif error == "LIMIT_REACHED": msg = "Server đã đạt giới hạn 50 Embed!"
            return await interaction.followup.send(f"❌ {msg}")

        # Lấy lại data vừa tạo để đưa vào View
        embed_data = await load_embed(guild.id, name)

        key = f"{guild.id}:{name}"
        _cleanup_views(key)
        
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        # GIỮ NGUYÊN TEXT HƯỚNG DẪN CỦA NGUYỆT
        msg = await interaction.followup.send(
            content=(
                f"✅ Đã khởi tạo thành công embed `{name}`\n\n"
                "Sử dụng các nút bên dưới để thiết kế nội dung.\n\n"
                "• **Edit Title** → Tiêu đề chính\n"
                "• **Edit Description** → Nội dung mô tả\n"
                "• **Set Image** → Link ảnh (URL)\n"
                "• **Edit Color** → Mã màu Hex (Ví dụ: #5865F2)\n"
                "• **Reaction Role** → Gán Emoji và Role cho người dùng tự lấy\n"
                "• **Save Embed** → Lưu vào bộ nhớ (Bắt buộc)\n\n"
                "• Sử dụng lệnh `/p embed show` để gửi kết quả vào kênh."
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
        
        # BẮT BUỘC AWAIT: Load dữ liệu từ đĩa
        data = await load_embed(interaction.guild.id, name)
        if not data: 
            return await interaction.followup.send(f"❌ Không tìm thấy embed `{name}`.")

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
        # BẮT BUỘC AWAIT
        data = await load_embed(interaction.guild.id, name)
        if not data: 
            return await interaction.response.send_message(f"❌ Không tìm thấy `{name}`.", ephemeral=True)
        
        await interaction.response.send_message(f"⌛ Đang gửi embed `{name}`...", ephemeral=True)
        
        # Gửi thật
        await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=name)

    @app_commands.command(name="delete", description="Xóa Embed vĩnh viễn")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        # BẮT BUỘC AWAIT
        await delete_embed(interaction.guild.id, name)
        _cleanup_views(f"{interaction.guild.id}:{name}")
        await interaction.response.send_message(f"🗑️ Embed `{name}` đã được xoá vĩnh viễn.", ephemeral=True)

# =============================
# INJECTION
# =============================

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "embed" for c in p_cmd.commands):
            p_cmd.add_command(EmbedGroup())
            print("[LOAD] Success: commands.embed.embed_group", flush=True)
    else:
        print("[ERROR] Không tìm thấy lệnh /p!", flush=True)
