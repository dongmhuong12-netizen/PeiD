import asyncio


class VoiceService:
    def __init__(self, bot):
        self.bot = bot

    async def start(self):
        await self.bot.wait_until_ready()

        # 🔥 allow gateway stable
        await asyncio.sleep(10)

        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    await self.bot.voice_manager.ensure(guild)

            except Exception as e:
                print("[VOICE SERVICE ERROR]", repr(e))

            await asyncio.sleep(20)
