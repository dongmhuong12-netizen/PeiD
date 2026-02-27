import discord
from discord.ext import commands
from discord import app_commands

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import (
    load_embed,
    delete_embed,
    get_all_embed_names
)

from core.greet_leave import GreetGroup, LeaveGroup, GreetLeaveListener
from core.booster import BoosterGroup, BoosterListener


# =============================
# AUTOCOMPLETE
# =============================

async def embed_name_autocomplete(
    interaction: discord.Interaction,
    current: str
):
    names = get_all_embed_names()

    return [
        app_commands.Choice(name=name, value=name)
        for name in names
        if current.lower() in name.lower()
    ][:25]


# =============================
# EMBED SUBGROUP
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="Embed management commands")

    @app_commands.command(name="create", description="Create a new embed UI")
    async def create(self, interaction: discord.Interaction, name: str):

        existing = load_embed(name)
        if existing:
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`. "
                f"Nếu tạo embed mà không tìm thấy, thử tìm embed đó bằng cách dùng lệnh /p embed edit.",
                ephemeral=True
            )
            return

        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        embed_data = {
            "title": "New Embed",
            "description": "Edit using buttons below.",
            "color": 0x5865F2
        }

        view = EmbedUIView(name, embed_data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=(
                f"Đã tạo embed với tên `{name}`\n\n"
                "Sử dụng các nút bên dưới để chỉnh sửa embed.\n\n"
                "• Edit Title → Chỉnh sửa tiêu đề\n"
                "• Edit Description → Chỉnh sửa mô tả\n"
                "• Set Image → Đặt ảnh cho embed\n"
                "• Edit Color → Đổi màu (mã hex)\n"
                "• Save Embed → Lưu embed\n"
                "• Delete Embed → Xoá embed vĩnh viễn\n\n"
                "• Bạn có thể sử dụng embed này để tạo tin nhắn chào mừng, rời đi, hoặc các banner hệ thống khi dùng lệnh /p embed show.\n\n"
                "• Lưu ý: hãy Save sau khi chỉnh sửa. Nếu không embed sẽ không được lưu lại, hoặc sẽ bị coi là không tồn tại nếu chưa từng Save.\n"
                "• Nếu có thắc mắc, dùng lệnh `/help` hoặc tham gia server hỗ trợ."
            ),
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

    @app_commands.command(name="edit", description="Edit existing embed")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không tìm thấy.",
                ephemeral=True
            )
            return

        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        view = EmbedUIView(name, data)
        embed = view.build_embed()

        await interaction.response.send_message(
            content=f"Bạn đang chỉnh sửa embed `{name}`.",
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message

    @app_commands.command(name="delete", description="Delete embed")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể dùng lệnh.",
                ephemeral=True
            )
            return

        if name in ACTIVE_EMBED_VIEWS:
            for view in ACTIVE_EMBED_VIEWS[name]:
                try:
                    if view.message:
                        await view.message.delete()
                except:
                    pass
                view.stop()

            ACTIVE_EMBED_VIEWS[name] = []

        delete_embed(name)

        await interaction.response.send_message(
            f"Embed `{name}` đã được xoá vĩnh viễn, có thể tạo embed mới bằng tên của embed này.",
            ephemeral=True
        )

    @app_commands.command(name="show", description="Send embed to channel")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str):

        data = load_embed(name)

        if not data:
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể gửi.",
                ephemeral=True
            )
            return

        color_value = data.get("color")
        if color_value is None:
            color_value = 0x2F3136

        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=color_value
        )

        if data.get("image"):
            embed.set_image(url=data["image"])

        await interaction.channel.send(embed=embed)
        await interaction.response.send_message(
            f"Embed `{name}` đã được gửi.",
            ephemeral=True
        )


# =============================
# MAIN /p GROUP
# =============================

class PGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="p", description="Main command group")
        self.add_command(EmbedGroup())
        self.add_command(GreetGroup())
        self.add_command(LeaveGroup())
        self.add_command(BoosterGroup())


# =============================
# COG
# =============================

class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
    await bot.add_cog(GreetLeaveListener(bot))
    await bot.add_cog(BoosterListener(bot))

    # 🔒 ĐẢM BẢO KHÔNG BAO GIỜ ADD TRÙNG GROUP p
    if bot.tree.get_command("p") is None:
        bot.tree.add_command(PGroup())
