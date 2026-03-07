import discord
import copy
import os
import json
import threading
from typing import Union
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"

file_lock = threading.Lock()


# =========================
# REACTION STORAGE
# =========================

def load_reaction_data():

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_reaction_data(data):

    os.makedirs("data", exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    with file_lock:

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        os.replace(temp_file, DATA_FILE)


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

        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        embed_copy = copy.deepcopy(embed_data)

        # =========================
        # APPLY VARIABLES
        # =========================

        embed_copy = apply_variables(embed_copy, guild, member)

        # =========================
        # COLOR FIX
        # =========================

        color = embed_copy.get("color")

        if isinstance(color, str):
            color = color.replace("#", "").replace("0x", "")
            embed_copy["color"] = int(color, 16)

        embed = discord.Embed(
            title=embed_copy.get("title"),
            description=embed_copy.get("description"),
            color=embed_copy.get("color", 0x2F3136)
        )

        # =========================
        # IMAGE
        # =========================

        image = embed_copy.get("image")

        if image:
            if isinstance(image, dict):
                embed.set_image(url=image.get("url"))
            else:
                embed.set_image(url=image)

        # =========================
        # THUMBNAIL
        # =========================

        thumbnail = embed_copy.get("thumbnail")

        if thumbnail:
            if isinstance(thumbnail, dict):
                embed.set_thumbnail(url=thumbnail.get("url"))
            else:
                embed.set_thumbnail(url=thumbnail)

        # =========================
        # FOOTER
        # =========================

        footer = embed_copy.get("footer")

        if isinstance(footer, dict):
            embed.set_footer(text=footer.get("text"))

        # =========================
        # AUTHOR
        # =========================

        author = embed_copy.get("author")

        if isinstance(author, dict):
            embed.set_author(name=author.get("name"))

        # =========================
        # FIELDS
        # =========================

        fields = embed_copy.get("fields")

        if fields:
            for field in fields:

                name = field.get("name")
                value = field.get("value")

                if name and value:

                    embed.add_field(
                        name=name,
                        value=value,
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
        # REACTION ROLE RESTORE
        # =========================

        if embed_name:

            data = load_reaction_data()

            key = f"{guild.id}::embed::{embed_name}"

            old_config = data.get(key)

            if old_config and "groups" in old_config:

                config = copy.deepcopy(old_config)

                # ADD REACTIONS
                for group in config.get("groups", []):

                    emojis = group.get("emojis", [])

                    for emoji in emojis:

                        try:
                            await message.add_reaction(emoji)
                        except:
                            pass

                # SAVE NEW CONFIG WITH MESSAGE ID
                config["guild_id"] = guild.id
                config["embed_name"] = embed_name

                data[str(message.id)] = config

                if key in data:
                    del data[key]

                save_reaction_data(data)

        return True


    except Exception as e:
        print("Embed send error:", e)
        return False
