import asyncio
import discord

from .booster_engine import assign_correct_level


# ==============================
# SYNC ONE MEMBER
# ==============================

async def sync_member(member: discord.Member):

    if member.bot:
        return

    if not member.premium_since:
        return

    try:
        await assign_correct_level(member)
    except Exception:
        pass


# ==============================
# SYNC ONE GUILD (BOOSTERS ONLY)
# ==============================

async def sync_guild(guild: discord.Guild):

    boosters = guild.premium_subscribers

    if not boosters:
        return

    for member in boosters:

        await sync_member(member)

        # tránh rate limit
        await asyncio.sleep(0.25)


# ==============================
# SYNC ALL GUILDS
# ==============================

async def sync_all_guilds(bot):

    for guild in bot.guilds:

        if guild.unavailable:
            continue

        await sync_guild(guild)

        # nghỉ giữa các server
        await asyncio.sleep(2)


# ==============================
# DAILY FULL RESYNC
# ==============================

async def daily_sync_loop(bot):

    await bot.wait_until_ready()

    # chờ thêm để member cache ổn định
    await asyncio.sleep(10)

    while not bot.is_closed():

        await sync_all_guilds(bot)

        # 24 giờ
        await asyncio.sleep(86400)


# ==============================
# REALTIME BOOST EVENT
# ==============================

async def handle_member_update(before: discord.Member, after: discord.Member):

    if after.bot:
        return

    if before.premium_since != after.premium_since:

        await sync_member(after)
