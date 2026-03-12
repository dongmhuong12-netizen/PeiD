import discord
from datetime import datetime, timezone

from .booster_storage import get_guild_config


# ==============================
# CALCULATE BOOST DAYS
# ==============================

def calculate_boost_days(member: discord.Member):

    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    return (now - member.premium_since).days


# ==============================
# GET MEMBER BOOST LEVEL
# ==============================

def get_member_level(boost_days: int, levels: dict):

    current_level = 1

    for lvl, data in levels.items():

        days = data.get("days")

        if days is None:
            continue

        lvl = int(lvl)

        if boost_days >= days:
            current_level = max(current_level, lvl)

    return current_level


# ==============================
# GET ROLE FOR LEVEL
# ==============================

def get_level_role(guild: discord.Guild, config: dict, level: int):

    if level == 1:
        role_id = config.get("booster_role")
        return guild.get_role(role_id) if role_id else None

    level_data = config["levels"].get(str(level))

    if not level_data:
        return None

    role_id = level_data.get("role")

    if not role_id:
        return None

    return guild.get_role(role_id)


# ==============================
# GET ALL BOOSTER SYSTEM ROLES
# ==============================

def get_all_booster_roles(guild: discord.Guild, config: dict):

    roles = []

    booster_role_id = config.get("booster_role")

    if booster_role_id:
        role = guild.get_role(booster_role_id)
        if role:
            roles.append(role)

    for lvl in config["levels"].values():

        role_id = lvl.get("role")

        if not role_id:
            continue

        role = guild.get_role(role_id)

        if role:
            roles.append(role)

    return roles


# ==============================
# REMOVE ALL BOOSTER ROLES
# ==============================

async def clear_level_roles(member: discord.Member, config: dict):

    booster_roles = get_all_booster_roles(member.guild, config)

    roles_to_remove = [
        role for role in booster_roles
        if role in member.roles
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Booster level update")


# ==============================
# ASSIGN CORRECT BOOST ROLE
# ==============================

async def assign_correct_level(member: discord.Member):

    config = await get_guild_config(member.guild.id)

    if not config:
        return None

    # Nếu không boost → remove role
    if not member.premium_since:

        await clear_level_roles(member, config)
        return None

    boost_days = calculate_boost_days(member)

    level = get_member_level(boost_days, config["levels"])

    target_role = get_level_role(member.guild, config, level)

    if not target_role:
        return level

    # role hierarchy check
    bot_member = member.guild.me

    if target_role >= bot_member.top_role:
        return level

    # lấy toàn bộ role hệ booster
    booster_roles = get_all_booster_roles(member.guild, config)

    # nếu member đã có role đúng
    if target_role in member.roles:

        # remove role booster khác nếu có
        wrong_roles = [
            r for r in booster_roles
            if r in member.roles and r != target_role
        ]

        if wrong_roles:
            await member.remove_roles(*wrong_roles, reason="Booster level correction")

        return level

    # remove role booster cũ
    roles_to_remove = [
        r for r in booster_roles
        if r in member.roles
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Booster level update")

    # add role mới
    await member.add_roles(target_role, reason="Booster level update")

    return level
