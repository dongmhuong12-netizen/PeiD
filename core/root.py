import điscord
from discord import app_commands
from discord.ext import commands

from storage.embed_storage import EmbedStorage
from core.embed_ui import EmbedUIView


class Root(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.embed_storage = EmbedStorage()

    # =========================
    # GROUP CHA /p
    # =========================
    p = app_commands.Group(name="p", description="Panel commands")

    # =========================
    # SUBGROUP /p embed
    # =========================
    embed = app_commands.Group(
        name="embed",
        description="Embed management",
        parent=p
    )

    # =========================
    # CREATE
    # =========================
    @embed.command(name="create", description="Tạo embed mới")
    async def create(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if self.embed_storage.exists(name):
            await interaction.response.send_message(
                f"Đã có embed tồn tại với tên `{name}`, không thể tạo. "
                "Nếu không tìm thấy embed với tên tương ứng, hãy dùng lệnh /p embed edit để tìm.",
                ephemeral=True
            )
            return

        embed_data = {
            "title": f"Embed: {name}",
            "description": "Embed mới được tạo. Hãy chỉnh sửa nội dung.",
            "color": 0x5865F2
        }

        self.embed_storage.save(name, embed_data)

        embed = discord.Embed(
            title=embed_data["title"],
            description=embed_data["description"],
            color=embed_data["color"]
        )

        view = EmbedUIView(self, name)

        await interaction.response.send_message(
            f"Đã tạo embed với tên `{name}`\n\n"
            "Sử dụng các nút bên dưới để chỉnh sửa embed.\n\n"
            "• Edit Title → Chỉnh sửa tiêu đề\n"
            "• Edit Description → Chỉnh sửa mô tả\n"
            "• Set Image → Đặt ảnh cho embed\n"
            "• Edit Color → Đổi màu (mã hex)\n"
            "• Save Embed → Lưu embed\n"
            "• Delete Embed → Xoá embed vĩnh viễn\n\n"
            "• Bạn có thể sử dụng embed này để tạo tin nhắn chào mừng, rời đi, "
            "hoặc các banner hệ thống khi dùng lệnh `/p embed show`.\n\n"
            "• Lưu ý: hãy Save sau khi chỉnh sửa. Nếu không embed sẽ không "
            "được lưu lại, hoặc sẽ bị coi là không tồn tại nếu chưa từng Save.\n\n"
            "• Nếu có thắc mắc, dùng lệnh `/help` hoặc tham gia server hỗ trợ.",
            embed=embed,
            view=view
        )

    # =========================
    # EDIT
    # =========================
    @embed.command(name="edit", description="Chỉnh sửa embed")
    async def edit(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not self.embed_storage.exists(name):
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không tìm thấy.",
                ephemeral=True
            )
            return

        embed_data = self.embed_storage.get(name)

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            color=embed_data.get("color", 0x5865F2)
        )

        if embed_data.get("image"):
            embed.set_image(url=embed_data["image"])

        view = EmbedUIView(self, name)

        await interaction.response.send_message(
            f"Đang chỉnh sửa embed `{name}`",
            embed=embed,
            view=view
        )

    # =========================
    # DELETE
    # =========================
    @embed.command(name="delete", description="Xoá embed")
    async def delete(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not self.embed_storage.exists(name):
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại, không thể dùng lệnh.",
                ephemeral=True
            )
            return

        self.embed_storage.delete(name)

        await interaction.response.send_message(
            f"Đã xoá embed `{name}` thành công.",
            ephemeral=True
        )

    # =========================
    # SHOW
    # =========================
    @embed.command(name="show", description="Hiển thị embed")
    async def show(self, interaction: discord.Interaction, name: str):
        name = name.lower()

        if not self.embed_storage.exists(name):
            await interaction.response.send_message(
                f"Embed tên `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        embed_data = self.embed_storage.get(name)

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            color=embed_data.get("color", 0x5865F2)
        )

        if embed_data.get("image"):
            embed.set_image(url=embed_data["image"])

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Root(bot))
