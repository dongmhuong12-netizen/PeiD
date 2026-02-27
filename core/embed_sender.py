import discord
import copy
from typing import Union
from core.variable_engine import apply_variables


async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None
):
    try:
        embed_copy = copy.deepcopy(embed_data)
        embed_copy = apply_variables(embed_copy, guild, member)

        if "color" in embed_copy and isinstance(embed_copy["color"], str):
            c = embed_copy["color"].replace("#", "").replace("0x", "")
            embed_copy["color"] = int(c, 16)

        embed = discord.Embed.from_dict(embed_copy)

    except Exception as e:
        print("Embed error:", e)
        return False

    if isinstance(destination, discord.Interaction):
        if destination.response.is_done():
            await destination.followup.send(embed=embed)
        else:
            await destination.response.send_message(embed=embed)
    else:
        await destination.send(embed=embed)

    return True
