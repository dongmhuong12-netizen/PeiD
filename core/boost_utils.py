import discord
from datetime import datetime, timezone


# ==============================
# CALCULATE BOOST DAYS
# ==============================

def get_boost_days(member: discord.Member) -> int:
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    return (now - member.premium_since).days


# ==============================
# CALCULATE MEMBER LEVEL ROLE
# ==============================

def calculate_level_role(member: discord.Member, booster_role, levels: list):

    if not booster_role:
        return None

    boost_days = get_boost_days(member)

    target_role = booster_role

    for lvl in levels:
        if boost_days >= lvl["days"]:
            role = member.guild.get_role(lvl["role"])
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
        role = guild.get_role(lvl["role"])
        if role:
            roles.append(role)

    return roles


# ==============================
# CLEANUP DELETED ROLES
# ==============================

def cleanup_deleted_roles(guild: discord.Guild, levels: list):

    cleaned = []
    removed = False

    for lvl in levels:
        role = guild.get_role(lvl["role"])

        if role:
            cleaned.append(lvl)
        else:
            removed = True

    return cleaned, removed


# ==============================
# VALIDATE LEVEL CONFIG
# ==============================

def validate_levels(levels: list, booster_role_id: int):

    if len(levels) > 100:
        return False, "Level vượt quá giới hạn 100."

    role_set = set()
    prev_days = 0

    for lvl in levels:

        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            return False, "Level thiếu role hoặc days."

        if role_id == booster_role_id:
            return False, "Role level không được trùng booster role."

        if role_id in role_set:
            return False, "Role level bị trùng."

        role_set.add(role_id)

        if days <= prev_days:
            return False, "Days phải tăng dần theo level."

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
