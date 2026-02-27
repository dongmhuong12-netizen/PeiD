import discord
from typing import Union
from core.variable_engine import apply_variables


async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None
):
    # 🔥 Always apply variables
    embed_data = apply_variables(embed_data, guild, member)

    embed = discord.Embed.from_dict(embed_data)

    if isinstance(destination, discord.Interaction):
        if destination.response.is_done():
            await destination.followup.send(embed=embed)
        else:
            await destination.response.send_message(embed=embed)
    else:
        await destination.send(embed=embed)
