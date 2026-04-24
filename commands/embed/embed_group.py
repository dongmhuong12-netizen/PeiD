import discord
from discord import app_commands
from discord.ext import commands
from core.root import Root

# Khởi tạo Group Embed độc lập
embed_group = app_commands.Group(
    name="embed",
    description="Hệ thống quản lý và thiết kế Embed chuyên nghiệp"
)

class EmbedGroupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Đăng ký Group vào lệnh chính /p của Root
        # Thực hiện bên trong Cog giúp đảm bảo Root đã Online
        root: Root = bot.get_cog("Root")
        if root and hasattr(root, "p"):
            # Kiểm tra tránh đăng ký trùng lặp nếu Cog reload
            if embed_group.name not in [cmd.name for cmd in root.p.commands]:
                root.p.add_command(embed_group)

async def setup(bot):
    await bot.add_cog(EmbedGroupCog(bot))
