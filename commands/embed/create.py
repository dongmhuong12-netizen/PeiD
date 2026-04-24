import discord
from discord.ext import commands
from core.root import Root
from core.embed_ui import EmbedUIView
from core.embed_storage import load_embed
from core.state import State # Tích hợp não bộ bền vững

class EmbedCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Đăng ký lệnh vào Group "embed" của Root
        root: Root = bot.get_cog("Root")
        if root and hasattr(root, "embed"):
            root.embed.add_command(self.create)

    @discord.app_commands.command(
        name="create",
        description="Khởi tạo hoặc chỉnh sửa một Embed"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh này chỉ có thể dùng trong Server.",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        
        # 1. Tải dữ liệu cũ nếu có
        data = load_embed(guild_id, name)
        is_edit = data is not None

        if not data:
            data = {
                "title": f"New Embed: {name}",
                "description": "Nhấn các nút bên dưới để bắt đầu thiết kế nội dung.",
                "color": 0x5865F2,
                "image": None
            }

        # 2. Khởi tạo UI View
        view = EmbedUIView(
            guild_id=guild_id,
            name=name,
            data=data
        )

        # TIÊU CHUẨN 100K+: Đăng ký View vào hệ thống Persistent của Discord
        # Giúp các nút bấm không bị "liệt" sau khi Bot restart
        self.bot.add_view(view)

        # 3. Build và Gửi bản xem trước
        embed = view.build_embed(interaction.guild, interaction.user)
        
        # Thêm Footer chỉ dẫn để Admin không bị quên tên Embed đang chỉnh
        embed.set_footer(text=f"Editor: {name} | {'Đang chỉnh sửa' if is_edit else 'Tạo mới'}")

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        # 4. Lưu vết tin nhắn vào View và State
        message = await interaction.original_response()
        view.message = message
        
        # Đăng ký ID tin nhắn này vào não bộ để các hệ thống khác (như Show/Edit) nhận diện được
        await State.atomic_embed_register(interaction.guild.id, name, message.id)


async def setup(bot):
    await bot.add_cog(EmbedCreate(bot))
