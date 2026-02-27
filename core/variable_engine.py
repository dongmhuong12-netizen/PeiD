import json
import discord
from typing import Union


def build_variables(
    guild: discord.Guild,
    member: discord.Member | None = None
) -> dict:

    variables = {}

    if member:
        variables.update({
            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_display}": member.display_name,
            "{user_id}": str(member.id),
            "{user_avatar}": member.display_avatar.url,
            "{account_created}": member.created_at.strftime("%d/%m/%Y"),
            "{joined_at}": member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Không rõ",
        })

    variables.update({
        "{server}": guild.name,
        "{server_id}": str(guild.id),
        "{member_count}": str(guild.member_count),
        "{boost_count}": str(guild.premium_subscription_count),
        "{boost_level}": str(guild.premium_tier),
        "{role_count}": str(len(guild.roles)),
        "{channel_count}": str(len(guild.channels)),
        "{online_count}": str(len([
            m for m in guild.members
            if m.status != discord.Status.offline
        ])),
    })

    return variables


def apply_variables(
    data: Union[str, dict],
    guild: discord.Guild,
    member: discord.Member | None = None
) -> Union[str, dict]:

    variables = build_variables(guild, member)

    if isinstance(data, str):
        for key, value in variables.items():
            data = data.replace(key, value)
        return data

    if isinstance(data, dict):
        data_str = json.dumps(data)
        for key, value in variables.items():
            data_str = data_str.replace(key, value)
        return json.loads(data_str)

    return data
