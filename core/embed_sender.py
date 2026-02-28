import discord
import copy
import os
import json
from typing import Union
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"


def load_reaction_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None
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
        # ===== SEND MESSAGE =====
        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                message = await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
                message = await destination.original_response()
        else:
            message = await destination.send(embed=embed)

        # ===== REACTION ROLE RESTORE =====
        if embed_name:
            data = load_reaction_data()

            old_message_id = None
            old_config = None

            # tìm config theo embed_name
            for msg_id, config in data.items():
                if config.get("embed_name") == embed_name:
                    old_message_id = msg_id
                    old_config = config
                    break

            if old_config and "groups" in old_config:

                # 🔥 add emoji của tất cả group
                for group in old_config.get("groups", []):
                    for emoji in group.get("emojis", []):
                        try:
                            await message.add_reaction(emoji)
                        except:
                            pass

                # ghi message_id mới
                data[str(message.id)] = old_config
                data[str(message.id)]["embed_name"] = embed_name

                # xoá message cũ
                if old_message_id and old_message_id in data:
                    del data[old_message_id]

                save_reaction_data(data)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
