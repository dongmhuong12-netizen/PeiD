import discord
import copy
import os
import json
from typing import Union
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"


# =========================
# REACTION STORAGE
# =========================

def load_reaction_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================
# SEND EMBED
# =========================

async def send_embed(
    destination: Union[discord.TextChannel, discord.Interaction],
    embed_data: dict,
    guild: discord.Guild,
    member: discord.Member | None = None,
    embed_name: str | None = None
):
    try:
        # Nếu là interaction mà không truyền member
        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        embed_copy = copy.deepcopy(embed_data)

        # APPLY VARIABLES
        embed_copy = apply_variables(embed_copy, guild, member)

        # FIX COLOR STRING
        if "color" in embed_copy:
            color = embed_copy["color"]
            if isinstance(color, str):
                color = color.replace("#", "").replace("0x", "")
                embed_copy["color"] = int(color, 16)

        # =========================
        # BUILD EMBED
        # =========================

        embed = discord.Embed(
            title=embed_copy.get("title"),
            description=embed_copy.get("description"),
            color=embed_copy.get("color", 0x2F3136)
        )

        # IMAGE
        if embed_copy.get("image"):
            if isinstance(embed_copy["image"], dict):
                embed.set_image(url=embed_copy["image"].get("url"))
            else:
                embed.set_image(url=embed_copy["image"])

        # THUMBNAIL
        if embed_copy.get("thumbnail"):
            if isinstance(embed_copy["thumbnail"], dict):
                embed.set_thumbnail(url=embed_copy["thumbnail"].get("url"))
            else:
                embed.set_thumbnail(url=embed_copy["thumbnail"])

        # FOOTER
        if embed_copy.get("footer"):
            footer = embed_copy["footer"]
            if isinstance(footer, dict):
                embed.set_footer(text=footer.get("text"))

        # AUTHOR
        if embed_copy.get("author"):
            author = embed_copy["author"]
            if isinstance(author, dict):
                embed.set_author(name=author.get("name"))

        # FIELDS
        if embed_copy.get("fields"):
            for field in embed_copy["fields"]:
                if field.get("name") and field.get("value"):
                    embed.add_field(
                        name=field.get("name"),
                        value=field.get("value"),
                        inline=field.get("inline", False)
                    )

    except Exception as e:
        print("Embed build error:", e)
        return False

    try:
        # =========================
        # SEND MESSAGE
        # =========================

        if isinstance(destination, discord.Interaction):
            if destination.response.is_done():
                message = await destination.followup.send(embed=embed)
            else:
                await destination.response.send_message(embed=embed)
                message = await destination.original_response()
        else:
            message = await destination.send(embed=embed)

        # =========================
        # REACTION ROLE RESTORE (FIXED)
        # =========================

        if embed_name:
            data = load_reaction_data()

            # 🔥 LẤY ĐÚNG KEY GỐC
            key = f"{guild.id}::embed::{embed_name}"
            old_config = data.get(key)

            if old_config and "groups" in old_config:

                # 🔥 ADD FULL EMOJI
                for group in old_config.get("groups", []):
                    for emoji in group.get("emojis", []):
                        try:
                            await message.add_reaction(emoji)
                        except Exception as e:
                            print("Reaction add error:", e)

                # 🔥 CHUYỂN CONFIG SANG MESSAGE.ID
                data[str(message.id)] = old_config
                data[str(message.id)]["guild_id"] = guild.id
                data[str(message.id)]["embed_name"] = embed_name

                # 🔥 XOÁ KEY CŨ
                if key in data:
                    del data[key]

                save_reaction_data(data)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
