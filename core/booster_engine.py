import discord
from datetime import datetime, timezone

from .booster_storage import get_guild_config, save_guild_config


# ==============================
# CALCULATE BOOST DAYS
# ==============================

def calculate_boost_days(member: discord.Member):
    if not member.premium_since:
        return 0

    now = datetime.now(timezone.utc)
    days = (now - member.premium_since).days
    return max(0, days)


# ==============================
# CLEAN INVALID LEVELS
# ==============================

async def clean_invalid_levels(guild: discord.Guild, config: dict):
    levels = config.get("levels", [])
    new_levels = []
    changed = False

    for lvl in levels:
        role_id = lvl.get("role")
        days = lvl.get("days")

        if role_id is None or days is None:
            continue

        role = guild.get_role(role_id)

        if not role:
            changed = True
            continue

        new_levels.append({
            "role": role_id,
            "days": days
        })

    if changed:
        config["levels"] = new_levels
        await save_guild_config(guild.id, config)

    return config


# ==============================
# GET TARGET LEVEL
# ==============================

def get_target_level(boost_days: int, levels: list):
    if not levels:
        return 1

    current_level = 1

    for index, lvl in enumerate(levels):
        days = lvl.get("days")

        if days is None:
            continue

        if boost_days >= days:
            current_level = index + 1

    return current_level


# ==============================
# GET ROLE FOR LEVEL
# ==============================

def get_role_for_level(guild: discord.Guild, config: dict, target_level: int):
    levels = config.get("levels", [])

    index = target_level - 1

    if index < 0 or index >= len(levels):
        return None

    role_id = levels[index].get("role")
    if not role_id:
        return None

    return guild.get_role(role_id)


# ==============================
# GET ALL BOOSTER ROLES
# ==============================

def get_all_booster_roles(guild: discord.Guild, config: dict):
    roles = set()

    for lvl in config.get("levels", []):
        role_id = lvl.get("role")
        if not role_id:
            continue

        role = guild.get_role(role_id)
        if role:
            roles.add(role)

    return list(roles)


# ==============================
# REMOVE ALL BOOSTER ROLES
# ==============================

async def clear_level_roles(member: discord.Member, config: dict):
    booster_roles = get_all_booster_roles(member.guild, config)

    bot_member = member.guild.me
    if not bot_member:
        return

    roles_to_remove = [
        r for r in booster_roles
        if r in member.roles and r < bot_member.top_role
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Booster clear")


# ==============================
# ASSIGN CORRECT LEVEL
# ==============================

async def assign_correct_level(member: discord.Member):
    config = await get_guild_config(member.guild.id)
    if not config:
        return None

    bot_member = member.guild.me
    if not bot_member:
        return None

    config = await clean_invalid_levels(member.guild, config)

    if not member.premium_since:
        await clear_level_roles(member, config)
        return None

    boost_days = calculate_boost_days(member)
    levels = config.get("levels", [])

    target_level = get_target_level(boost_days, levels)
    target_role = get_role_for_level(member.guild, config, target_level)

    if not target_role:
        return target_level

    if target_role >= bot_member.top_role:
        return target_level

    booster_roles = get_all_booster_roles(member.guild, config)

    if target_role in member.roles:
        wrong_roles = [
            r for r in booster_roles
            if r in member.roles
            and r != target_role
            and r < bot_member.top_role
        ]

        if wrong_roles:
            await member.remove_roles(*wrong_roles, reason="Booster correction")

        return target_level

    roles_to_remove = [
        r for r in booster_roles
        if r in member.roles and r < bot_member.top_role
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Booster update")

    await member.add_roles(target_role, reason="Booster level update")
    return target_level
