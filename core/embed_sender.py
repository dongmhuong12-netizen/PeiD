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

        # ===== FIX IMAGE FORMAT =====
        if "image" in embed_copy:
            img = embed_copy["image"]

            if isinstance(img, str):
                embed_copy["image"] = {"url": img}

            elif isinstance(img, dict):
                if not img.get("url"):
                    embed_copy.pop("image")

        if "thumbnail" in embed_copy:
            thumb = embed_copy["thumbnail"]

            if isinstance(thumb, str):
                embed_copy["thumbnail"] = {"url": thumb}

            elif isinstance(thumb, dict):
                if not thumb.get("url"):
                    embed_copy.pop("thumbnail")

        # ===== FIX EMPTY BLOCKS =====
        for key in ["author", "footer"]:
            if key in embed_copy and not embed_copy[key]:
                embed_copy.pop(key)

        # ===== FIX FIELDS =====
        if "fields" in embed_copy:
            embed_copy["fields"] = [
                f for f in embed_copy["fields"]
                if f.get("name") and f.get("value")
            ]
            if not embed_copy["fields"]:
                embed_copy.pop("fields")

        # ===== FIX COLOR =====
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
