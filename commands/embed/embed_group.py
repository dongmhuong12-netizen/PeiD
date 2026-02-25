from discord import app_commands
from core.root import Root


embed_group = app_commands.Group(
    name="embed",
    description="Embed management"
)

Root.p.add_command(embed_group)
