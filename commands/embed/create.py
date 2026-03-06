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

    view = EmbedUIView(interaction.guild.id, name, data)

    msg = await interaction.channel.send(
        embed=view.build_embed(),
        view=view
    )

    view.message = msg

    await interaction.response.send_message(
        f"Embed `{name}` editor created.",
        ephemeral=True
    )
