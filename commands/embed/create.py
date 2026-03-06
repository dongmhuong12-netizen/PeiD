import discord
from discord.ext import commands
from core.root import Root
from core.embed_ui import EmbedUIView


class EmbedCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        root: Root = bot.get_cog("Root")
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
        data = {
            "title": None,
            "description": None,
            "color": 0x5865F2,
            "image": None
        }

        view = EmbedUIView(
            guild_id=interaction.guild.id,
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
