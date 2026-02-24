import discord
import random
import json
import os

CONFIG_FILE = "boost_config.json"

DEFAULT_COLOR = 0xF48FB1
DEFAULT_MESSAGE = "Cảm ơn {user} đã boost server ✨"
DEFAULT_GIFS = [
    "https://media.tenor.com/3vR6kG9yFZkAAAAC/anime-thank-you.gif"
]

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def send_boost(guild, user):
    config = load_config()
    guild_conf = config.get(str(guild.id), {})

    channel_id = guild_conf.get("channel_id")
    role_id = guild_conf.get("role_id")
    message = guild_conf.get("message", DEFAULT_MESSAGE)
    gifs = guild_conf.get("gifs", DEFAULT_GIFS)

    channel = guild.get_channel(channel_id) if channel_id else None
    if not channel:
        return

    embed = discord.Embed(
        description=message.format(user=user.mention),
        color=DEFAULT_COLOR
    )

    embed.set_image(url=random.choice(gifs))
    await channel.send(embed=embed)

    if role_id:
        role = guild.get_role(role_id)
        if role and role not in user.roles:
            await user.add_roles(role)
