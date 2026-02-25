import discord
from discord import app_commands
from discord.ext import commands

from systems.embed.manager import EmbedManager


class EmbedCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = EmbedManager(bot.db)

    # Tạo group /p
    p_group = app_commands.Group(name="p", description="Pei main commands")

    # Tạo subgroup /p embed
    embed_group = app_commands.Group(
        name="embed",
        description="Quản lý embed"
    )

    # /p embed create
    @embed_group.command(name="create", description="Tạo một embed mới")
    @app_commands.describe(name="Tên embed")
    async def create_embed(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "Lệnh chỉ dùng trong server.",
                ephemeral=True
            )
            return

        try:
            await self.manager.create_embed(interaction.guild.id, name)

            await interaction.response.send_message(
                f"Đã tạo embed `{name}` thành công.",
                ephemeral=True
            )

        except ValueError as e:
            await interaction.response.send_message(
                str(e),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    cog = EmbedCommands(bot)

    # Gắn subgroup embed vào group p
    cog.p_group.add_command(cog.embed_group)

    # Thêm group p vào tree
    bot.tree.add_command(cog.p_group)

    await bot.add_cog(cog)
