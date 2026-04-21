import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed

from core.greet_leave import GreetGroup, LeaveGroup, GreetLeaveListener
from core.booster import BoostGroup, BoosterListener
from core.wellcome import WellcomeGroup, WellcomeListener


# =============================
# SAFE CLEANUP (FIX ONLY MEMORY / NO UI CHANGE)
# =============================

def _cleanup_views(key: str):
    views = ACTIVE_EMBED_VIEWS.get(key)
    if not views:
        return

    for view in list(views):
        try:
            if view.message:
                import asyncio
                asyncio.create_task(view.message.delete())
        except:
            pass

        try:
            view.stop()
        except:
            pass

    ACTIVE_EMBED_VIEWS[key] = []


# =============================
# AUTOCOMPLETE (UNCHANGED LOGIC)
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild_id = interaction.guild.id if interaction.guild else None

    if not guild_id:
        return []

    names = get_all_embed_names(guild_id)

    return [
        app_commands.Choice(name=name, value=name)
        for name in names
        if current.lower() in name.lower()
    ][:25]


# =============================
# EMBED GROUP
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Embed management commands")

    @app_commands.command(name="create", description="Create a new embed UI")
    async def create(self, interaction: discord.Interaction, name: str):

        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        existing = load_embed(interaction.guild.id, name)
        if existing:
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`. "
                f"Nếu không thấy embed, thử dùng /p embed edit.",
                ephemeral=True
            )
            return

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        embed_data = {
            "title": "Embed Mới",
            "description": "Dùng các nút bên dưới để chỉnh sửa embed.",
            "color": 0x5865F2
        }

        view = EmbedUIView(interaction.guild.id, name, embed_data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=(
                f"Đã tạo embed với tên `{name}`\n\n"
                "Sử dụng các nút bên dưới để chỉnh sửa embed.\n\n"
                "• Edit Title → Chỉnh sửa tiêu đề\n"
                "• Edit Description → Chỉnh sửa mô tả\n"
                "• Set Image → Đặt ảnh cho embed\n"
                "• Edit Color → Đổi màu (hex)\n"
                "• Reaction Role → gán role theo emoji\n"
                "• Save Embed → Lưu embed\n"
                "• Delete Embed → Xoá embed\n\n"
                "• Dùng /p embed show để gửi embed ra kênh\n"
                "• Nhớ Save để lưu dữ liệu"
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

        if not interaction.guild:
            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return

        data = load_embed(interaction.guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        view = EmbedUIView(interaction.guild.id, name, data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=f"Bạn đang chỉnh sửa embed `{name}`",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

        ACTIVE_EMBED_VIEWS.setdefault(key, []).append(view)

    @app_commands.command(name="delete", description="Delete embed")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):

        if not interaction.guild:
            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return

        data = load_embed(interaction.guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        key = f"{interaction.guild.id}:{name}"
        _cleanup_views(key)

        delete_embed(interaction.guild.id, name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá.",
            ephemeral=True
        )

    @app_commands.command(name="show", description="Send embed to channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):

        if not interaction.guild:
            await interaction.response.send_message(
                "Server only command.",
                ephemeral=True
            )
            return

        data = load_embed(interaction.guild.id, name)
        if not data:
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        await send_embed(
            interaction.channel,
            data,
            interaction.guild,
            interaction.user,
            embed_name=name
        )

        await interaction.response.send_message(
            f"Embed `{name}` đã được gửi.",
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
