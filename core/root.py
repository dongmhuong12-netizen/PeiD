# core/root.py
import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed

from core.greet_leave import GreetGroup, LeaveGroup, GreetLeaveListener
from core.booster import BoostGroup, BoosterListener
from core.wellcome import WellcomeGroup, WellcomeListener

import asyncio

# =============================
# SAFE AUTOCOMPLETE
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild:
        return []

    names = get_all_embed_names(guild.id)

    return [
        app_commands.Choice(name=name, value=name)
        for name in names
        if current.lower() in name.lower()
    ][:25]


# =============================
# SAFE CLEANUP (MULTI-SERVER FIX)
# =============================

def _cleanup_views(key: str):
    views = ACTIVE_EMBED_VIEWS.get(key)
    if not views:
        return

    for view in list(views):
        try:
            if getattr(view, "message", None):
                asyncio.create_task(view.message.delete())
        except:
            pass

        try:
            view.stop()
        except:
            pass

    ACTIVE_EMBED_VIEWS[key] = []


# =============================
# EMBED GROUP
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Embed management commands")

    @app_commands.command(name="create", description="Create a new embed UI")
    async def create(self, interaction: discord.Interaction, name: str):

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        existing = load_embed(guild.id, name)
        if existing:
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`. "
                f"Nếu tạo embed mà không tìm thấy, thử dùng lệnh **/p embed edit**.",
                ephemeral=True
            )
            return

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        embed_data = {
            "title": "Embed Mới",
            "description": "Dùng các nút bên dưới để chỉnh sửa.",
            "color": 0x5865F2
        }

        view = EmbedUIView(guild.id, name, embed_data)
        embed = view.build_embed()

        await interaction.response.send_message(
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

        message = await interaction.original_response()
        view.message = message

        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="edit", description="Edit existing embed")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str):

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        data = load_embed(guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không tìm thấy.",
                ephemeral=True
            )
            return

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        view = EmbedUIView(guild.id, name, data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=f"Bạn đang chỉnh sửa embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="delete", description="Delete embed")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        data = load_embed(guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể dùng lệnh.",
                ephemeral=True
            )
            return

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        delete_embed(guild.id, name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá vĩnh viễn.",
            ephemeral=True
        )

    @app_commands.command(name="show", description="Send embed to channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        data = load_embed(guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể show.",
                ephemeral=True
            )
            return

        await send_embed(interaction.channel, data, guild, interaction.user, embed_name=name)

        await interaction.response.send_message(
            f"Embed `{name}` show thành công.",
            ephemeral=True
        )


# =============================
# MAIN GROUP
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="Main command group")
        self.add_command(EmbedGroup())
        self.add_command(GreetGroup())
        self.add_command(LeaveGroup())
        self.add_command(BoostGroup())
        self.add_command(WellcomeGroup())


# =============================
# ROOT COG
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


# =============================
# SETUP
# =============================

async def setup(bot: commands.Bot):
    if bot.tree.get_command("p") is None:
        bot.tree.add_command(PGroup())

    await bot.add_cog(Root(bot))
    await bot.add_cog(GreetLeaveListener(bot))
    await bot.add_cog(BoosterListener(bot))
    await bot.add_cog(WellcomeListener(bot))
