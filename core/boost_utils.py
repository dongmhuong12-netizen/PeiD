import discord
from datetime import datetime, timezone


# ==============================
# CALCULATE BOOST DAYS
# ==============================

def get_boost_days(member: discord.Member) -> int:

    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)

    days = (now - member.premium_since).days

    if days < 0:
        return 0

    return days


# ==============================
# CALCULATE MEMBER LEVEL ROLE
# ==============================

def calculate_level_role(member: discord.Member, booster_role, levels: list):

    if not booster_role:
        return None

    boost_days = get_boost_days(member)

    target_role = booster_role

    for lvl in levels:

        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            continue

        if boost_days >= days:

            role = member.guild.get_role(role_id)

            if role:
                target_role = role

    return target_role


# ==============================
# GET ALL BOOSTER SYSTEM ROLES
# ==============================

def get_booster_roles(guild: discord.Guild, booster_role_id: int, levels: list):

    roles = []

    booster_role = guild.get_role(booster_role_id)

    if booster_role:
        roles.append(booster_role)

    for lvl in levels:

        role_id = lvl.get("role")

        if not role_id:
            continue

        role = guild.get_role(role_id)

        if role:
            roles.append(role)

    return roles


# ==============================
# CLEANUP DELETED ROLES
# ==============================

def cleanup_deleted_roles(guild: discord.Guild, levels: list):

    changed = False
    new_levels = []

    for lvl in levels:

        role_id = lvl.get("role")

        if not role_id:
            continue

        role = guild.get_role(role_id)

        # FIX: role bị xoá → remove level
        if not role:
            changed = True
            continue

        new_levels.append(lvl)

    return new_levels, changed


# ==============================
# VALIDATE LEVEL CONFIG
# ==============================

def validate_levels(levels: list, booster_role_id: int):

    role_set = set()
    prev_days = -1

    for i, lvl in enumerate(levels):

        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            return False, "Level phải có cả role và days."

        # FIX: level 1
        if i == 0:
            if days != 0:
                return False, "Level 1 phải = 0 ngày."
        else:
            if days <= prev_days:
                return False, "Days phải tăng dần theo level."

        if role_id == booster_role_id:
            return False, "Role level không được trùng booster role."

        if role_id in role_set:
            return False, "Role level bị trùng."

        role_set.add(role_id)
        prev_days = days

    return True, None


# ==============================
# REORDER LEVELS
# ==============================

def move_level_up(levels: list, index: int):

    if index <= 0:
        return levels

    levels[index - 1], levels[index] = levels[index], levels[index - 1]

    return levels


def move_level_down(levels: list, index: int):

    if index >= len(levels) - 1:
        return levels

    levels[index + 1], levels[index] = levels[index], levels[index + 1]

    return levels


# ==============================
# FIND MEMBER BOOST ROLE
# ==============================

def get_member_booster_role(member: discord.Member, booster_roles: list):

    for role in booster_roles:

        if role in member.roles:
            return role

    return None
