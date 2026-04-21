import discord
from discord.ext import commands
from core.root import Root
from core.embed_ui import EmbedUIView
from core.embed_storage import load_embed


class EmbedCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # SAFE: tránh crash nếu Root chưa load
        root: Root = bot.get_cog("Root")
        if root and hasattr(root, "embed"):
            root.embed.add_command(self.create)

    @discord.app_commands.command(
        name="create",
        description="Create a new embed"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        # 🔥 SAFE: tránh crash khi dùng ngoài server
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        # SAFE: normalize guild id (tránh mismatch string/int giữa hệ storage)
        guild_id = str(interaction.guild.id)

        data = load_embed(guild_id, name)

        if not data:
            data = {
                "title": None,
                "description": None,
                "color": 0x5865F2,
                "image": None
            }

        view = EmbedUIView(
            guild_id=guild_id,
            name=name,
            data=data
        )

        embed = view.build_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        message = await interaction.original_response()
        view.message = message


async def setup(bot):
    await bot.add_cog(EmbedCreate(bot))
