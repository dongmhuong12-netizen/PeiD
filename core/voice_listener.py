import discord
from discord.ext import commands


class VoiceListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id:
            return

        # bot bị kick hoặc disconnect
        if before.channel and not after.channel:
            print("[VOICE KICKED] auto recover")

            guild = member.guild
            data = self.bot.voice_manager

            # trigger restore next tick
            await self.bot.voice_manager.ensure_connected(guild)
