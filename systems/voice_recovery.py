import asyncio
import time
from core.voice_storage import get_all, set_voice


class VoiceRecovery:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.start_time = time.time()

    async def start(self):
        await self.bot.wait_until_ready()

        # 🔥 Render-safe startup delay
        await asyncio.sleep(15)

        while self.running and not self.bot.is_closed():
            try:
                data = get_all()

                for gid, cfg in data.items():
                    guild = self.bot.get_guild(int(gid))
                    if not guild:
                        continue

                    vc = guild.voice_client

                    # ❌ manual leave → skip
                    if cfg.get("manual_leave"):
                        continue

                    # ❌ disabled → skip
                    if not cfg.get("enabled", True):
                        continue

                    # ❌ cooldown reconnect protection
                    now = time.time()
                    last = cfg.get("last_reconnect", 0)
                    if now - last < 30:
                        continue

                    # 🔁 reconnect logic
                    if not vc or not vc.is_connected():
                        channel = guild.get_channel(cfg["channel_id"])

                        if not channel:
                            continue

                        try:
                            await channel.connect()

                            cfg["last_reconnect"] = now
                            set_voice(gid, cfg["channel_id"])

                            print(f"[VOICE RECOVER] {gid}")

                        except Exception as e:
                            cfg["last_error"] = str(e)
                            set_voice(gid, cfg["channel_id"])

            except Exception as e:
                print(f"[VOICE LOOP ERROR] {e}")

            await asyncio.sleep(60)
