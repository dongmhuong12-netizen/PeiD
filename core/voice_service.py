import asyncio


class VoiceService:
    def __init__(self, bot):
        self.bot = bot
        self.manager = bot.voice_manager
        self.running = False

    async def start(self):
        if self.running:
            return
        self.running = True

        while True:
            try:
                await self.tick()
            except Exception as e:
                print("[VOICE SERVICE ERROR]", repr(e))

            await asyncio.sleep(30)

    async def tick(self):
        for guild in self.bot.guilds:
            await self.manager.ensure_connected(guild)
