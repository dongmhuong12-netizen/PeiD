import asyncio
import discord

from .booster_engine import assign_correct_level


async def sync_member(member: discord.Member):

    try:
        await assign_correct_level(member)
    except Exception:
        pass


async def sync_guild(guild: discord.Guild):

    for member in guild.members:

        if member.bot:
            continue

        if member.premium_since:
            await sync_member(member)

        await asyncio.sleep(0.3)


async def sync_all_guilds(bot):

    for guild in bot.guilds:

        await sync_guild(guild)

        await asyncio.sleep(2)


async def daily_sync_loop(bot):

    await bot.wait_until_ready()

    while not bot.is_closed():

        await sync_all_guilds(bot)

        await asyncio.sleep(86400)
