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
        # Clone tránh phá dữ liệu gốc
        embed_copy = copy.deepcopy(embed_data)

        # Apply variables
        embed_copy = apply_variables(embed_copy, guild, member)

        # Loại bỏ key rỗng gây lỗi
        for key in ["image", "thumbnail", "author", "footer"]:
            if key in embed_copy and not embed_copy[key]:
                embed_copy.pop(key)

        # Chuẩn hoá color
        if "color" in embed_copy:
            color = embed_copy["color"]
            if isinstance(color, str):
                color = color.replace("#", "").replace("0x", "")
                embed_copy["color"] = int(color, 16)

        embed = discord.Embed.from_dict(embed_copy)

    except Exception as e:
        print("Embed build error:", e)
        return False

    try:
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
        else:
            await destination.send(embed=embed)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
