from discord.ext import commands


class VoiceListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id:
            return

        if before.channel and not after.channel:
            print("[VOICE DISCONNECTED]")
            # ❌ KHÔNG reconnect ở đây nữa


async def setup(bot):
    await bot.add_cog(VoiceListener(bot))
