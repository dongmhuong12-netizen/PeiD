import discord
from datetime import datetime, timezone

from .booster_storage import get_guild_config


def calculate_boost_days(member: discord.Member):

    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)

    delta = now - member.premium_since

    return delta.days


async def get_member_level(member: discord.Member):

    config = await get_guild_config(member.guild.id)

    levels = config["levels"]

    boost_days = calculate_boost_days(member)

    current_level = 1

    for lvl, data in levels.items():

        lvl = int(lvl)

        if boost_days >= data["days"]:
            current_level = max(current_level, lvl)

    return current_level


async def get_level_role(member: discord.Member, level: int):

    config = await get_guild_config(member.guild.id)

    if level == 1:
        role_id = config["booster_role"]
        return member.guild.get_role(role_id) if role_id else None

    level_data = config["levels"].get(str(level))

    if not level_data:
        return None

    return member.guild.get_role(level_data["role"])


async def clear_level_roles(member: discord.Member):

    config = await get_guild_config(member.guild.id)

    roles_to_remove = []

    booster_role_id = config["booster_role"]

    if booster_role_id:
        role = member.guild.get_role(booster_role_id)
        if role and role in member.roles:
            roles_to_remove.append(role)

    for lvl in config["levels"].values():
        role = member.guild.get_role(lvl["role"])
        if role and role in member.roles:
            roles_to_remove.append(role)

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove)


async def assign_correct_level(member: discord.Member):

    if not member.premium_since:
        await clear_level_roles(member)
        return None

    level = await get_member_level(member)

    role = await get_level_role(member, level)

    await clear_level_roles(member)

    if role:
        await member.add_roles(role)

    return level
