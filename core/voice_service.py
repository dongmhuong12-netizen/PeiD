import asyncio


class VoiceService:
    def __init__(self, bot):
        self.bot = bot

    async def start(self):
        while True:
            try:
                for guild in self.bot.guilds:
                    await self.bot.voice_manager.ensure_connected(guild)

            except Exception as e:
                print("[VOICE SERVICE ERROR]", repr(e))

            await asyncio.sleep(25)
