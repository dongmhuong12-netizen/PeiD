# core/embed_sender.py
import discord
import copy
import os
import json
import asyncio
from typing import Union
from core.variable_engine import apply_variables

DATA_FILE = "data/reaction_roles.json"

file_lock = asyncio.Lock()


# =========================
# REACTION STORAGE
# =========================

def load_reaction_data():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def save_reaction_data(data):
    os.makedirs("data", exist_ok=True)

    temp_file = DATA_FILE + ".tmp"

    async with file_lock:
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

    if not embed_data or not isinstance(embed_data, dict):
        return False

    try:

        if member is None and isinstance(destination, discord.Interaction):
            member = destination.user

        embed_copy = copy.deepcopy(embed_data)

        embed_copy = apply_variables(embed_copy, guild, member)

        color = embed_copy.get("color")

        if isinstance(color, str):
            try:
                color = color.replace("#", "").replace("0x", "")
                embed_copy["color"] = int(color, 16)
            except:
                embed_copy["color"] = 0x2F3136

        embed = discord.Embed(
            title=embed_copy.get("title"),
            description=embed_copy.get("description"),
            color=embed_copy.get("color", 0x2F3136)
        )

        image = embed_copy.get("image")
        if image:
            embed.set_image(url=image.get("url") if isinstance(image, dict) else image)

        thumbnail = embed_copy.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.get("url") if isinstance(thumbnail, dict) else thumbnail)

        footer = embed_copy.get("footer")
        if isinstance(footer, dict):
            embed.set_footer(text=footer.get("text"))

        author = embed_copy.get("author")
        if isinstance(author, dict):
            embed.set_author(name=author.get("name"))

        fields = embed_copy.get("fields")
        if isinstance(fields, list):
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
            bot_member = guild.me
            if not bot_member:
                return False

            perms = destination.permissions_for(bot_member)
            if not perms.send_messages or not perms.embed_links:
                return False

            message = await destination.send(embed=embed)

        # =========================
        # REACTION ROLE RESTORE
        # =========================

        if embed_name:

            data = load_reaction_data()

            key = f"{guild.id}::embed::{embed_name}"

            old_config = data.get(key)

            if isinstance(old_config, dict) and "groups" in old_config:

                config = copy.deepcopy(old_config)

                for group in config.get("groups", []):
                    emojis = group.get("emojis", [])

                    for emoji in emojis:
                        try:
                            await message.add_reaction(emoji)
                            await asyncio.sleep(0.2)
                        except:
                            pass

                config["guild_id"] = guild.id
                config["embed_name"] = embed_name

                data[str(message.id)] = config

                await save_reaction_data(data)

        return True

    except Exception as e:
        print("Embed send error:", e)
        return False
