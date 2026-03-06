import discord
from typing import Union
import time


def build_variables(
    guild: discord.Guild,
    member: discord.Member | None = None
) -> dict:

    variables = {}

    # =========================
    # MEMBER VARIABLES
    # =========================

    if member:

        joined_at = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Unknown"

        variables.update({

            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_display}": member.display_name,
            "{user_tag}": str(member),
            "{user_id}": str(member.id),

            "{user_avatar}": member.display_avatar.url,
            "{user_avatar_png}": member.display_avatar.replace(format="png").url,

            "{user_bot}": str(member.bot),

            "{user_created}": member.created_at.strftime("%d/%m/%Y"),
            "{user_joined}": joined_at,

            "{user_role_count}": str(len(member.roles) - 1),
            "{user_top_role}": member.top_role.name if member.top_role else "None",

        })

    # =========================
    # SERVER VARIABLES
    # =========================

    variables.update({

        "{server}": guild.name,
        "{server_name}": guild.name,
        "{server_id}": str(guild.id),

        "{server_owner}": guild.owner.mention if guild.owner else "Unknown",
        "{server_owner_id}": str(guild.owner_id),

        "{server_created}": guild.created_at.strftime("%d/%m/%Y"),

        "{server_icon}": guild.icon.url if guild.icon else "",
        "{server_icon_png}": guild.icon.replace(format="png").url if guild.icon else "",

        "{member_count}": str(guild.member_count or 0),

        "{bot_count}": str(sum(1 for m in guild.members if m.bot)),
        "{human_count}": str(sum(1 for m in guild.members if not m.bot)),

        "{boost_count}": str(guild.premium_subscription_count or 0),
        "{boost_level}": str(guild.premium_tier),

        "{role_count}": str(len(guild.roles)),
        "{channel_count}": str(len(guild.channels)),

        "{text_channel_count}": str(len(guild.text_channels)),
        "{voice_channel_count}": str(len(guild.voice_channels)),
        "{category_count}": str(len(guild.categories)),

        "{emoji_count}": str(len(guild.emojis)),
        "{sticker_count}": str(len(guild.stickers)),

        "{online_count}": str(sum(
            1 for m in guild.members
            if m.status != discord.Status.offline
        )),

    })

    # =========================
    # TIME VARIABLES
    # =========================

    variables.update({

        "{timestamp}": str(int(time.time())),
        "{unix}": str(int(time.time())),
        "{date}": discord.utils.utcnow().strftime("%d/%m/%Y"),
        "{time}": discord.utils.utcnow().strftime("%H:%M:%S"),

    })

    return variables


def apply_variables(
    data: Union[str, dict, list],
    guild: discord.Guild,
    member: discord.Member | None = None
) -> Union[str, dict, list]:

    variables = build_variables(guild, member)

    def replace_value(value):

        if isinstance(value, str):

            for key, val in variables.items():
                value = value.replace(key, val)

            return value

        if isinstance(value, dict):

            return {
                k: replace_value(v)
                for k, v in value.items()
            }

        if isinstance(value, list):

            return [
                replace_value(v)
                for v in value
            ]

        return value

    return replace_value(data)
