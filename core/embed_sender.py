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
        # Clone tránh sửa dữ liệu gốc
        embed_copy = copy.deepcopy(embed_data)

        # Apply biến
        embed_copy = apply_variables(embed_copy, guild, member)

        # ===== FIX BLOCK RỖNG =====
        for key in ["image", "thumbnail", "author", "footer"]:
            if key in embed_copy:
                value = embed_copy[key]

                # nếu rỗng hoặc url rỗng → xoá
                if not value or (isinstance(value, dict) and value.get("url") == ""):
                    embed_copy.pop(key)

        # ===== FIX FIELDS RỖNG =====
        if "fields" in embed_copy:
            embed_copy["fields"] = [
                f for f in embed_copy["fields"]
                if f.get("name") and f.get("value")
            ]
            if not embed_copy["fields"]:
                embed_copy.pop("fields")

        # ===== FIX COLOR STRING =====
        if "color" in embed_copy:
            color = embed_copy["color"]
            if isinstance(color, str):
                color = color.replace("#", "").replace("0x", "")
                embed_copy["color"] = int(color, 16)

        # Build embed
        embed = discord.Embed.from_dict(embed_copy)

    except Exception as e:
        print("Embed build error:", e)
        return False

    try:
        # Gửi embed
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
