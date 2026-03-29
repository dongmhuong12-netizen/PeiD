# core/booster_engine.py
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

    if days < 0:
        return 0

    return days


# ==============================
# CLEAN INVALID LEVELS (ROLE BỊ XOÁ)
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

        # role bị xoá → remove level
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

    for lvl in levels:

        level = lvl.get("level")
        days = lvl.get("days")

        if level is None or days is None:
            continue

        if boost_days >= days:
            current_level = max(current_level, level)

    return current_level


# ==============================
# GET ROLE FOR LEVEL
# ==============================

def get_role_for_level(guild: discord.Guild, config: dict, target_level: int):

    # Level 1 → booster role
    if target_level == 1:
        role_id = config.get("booster_role")
        return guild.get_role(role_id) if role_id else None

    for lvl in config.get("levels", []):

        if lvl.get("level") == target_level:

            role_id = lvl.get("role")
            if not role_id:
                return None

            return guild.get_role(role_id)

    return None


# ==============================
# GET ALL BOOSTER SYSTEM ROLES
# ==============================

def get_all_booster_roles(guild: discord.Guild, config: dict):

    roles = set()

    # booster role
    booster_role_id = config.get("booster_role")

    if booster_role_id:
        role = guild.get_role(booster_role_id)
        if role:
            roles.add(role)

    # level roles
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

    # =========================
    # CHECK BOOSTER ROLE
    # =========================
    booster_role_id = config.get("booster_role")
    booster_role = member.guild.get_role(booster_role_id) if booster_role_id else None

    # booster role bị xoá → disable hệ
    if booster_role_id and not booster_role:
        config["booster_role"] = None
        await save_guild_config(member.guild.id, config)
        return None

    # =========================
    # CLEAN LEVEL ROLE BỊ XOÁ
    # =========================
    config = await clean_invalid_levels(member.guild, config)

    # =========================
    # KHÔNG BOOST → REMOVE ALL
    # =========================
    if not member.premium_since:
        await clear_level_roles(member, config)
        return None

    boost_days = calculate_boost_days(member)

    levels = config.get("levels", [])

    target_level = get_target_level(boost_days, levels)

    target_role = get_role_for_level(member.guild, config, target_level)

    if not target_role:
        return target_level

    # bot không đủ quyền
    if target_role >= bot_member.top_role:
        return target_level

    booster_roles = get_all_booster_roles(member.guild, config)

    # =========================
    # ĐÃ CÓ ROLE ĐÚNG
    # =========================
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

    # =========================
    # REMOVE ALL ROLE HỆ
    # =========================
    roles_to_remove = [
        r for r in booster_roles
        if r in member.roles and r < bot_member.top_role
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Booster update")

    # =========================
    # ADD ROLE ĐÚNG
    # =========================
    await member.add_roles(target_role, reason="Booster level update")

    return target_level
