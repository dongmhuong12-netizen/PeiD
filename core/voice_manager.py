import discord
import asyncio
import time

from core.voice_storage import set_voice, remove_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}
        self.cooldowns = {}

    # =========================
    # LOCK PER GUILD
    # =========================
    def _lock(self, gid: int):
        if gid not in self.locks:
            self.locks[gid] = asyncio.Lock()
        return self.locks[gid]

    # =========================
    # COOLDOWN
    # =========================
    def _cooldown(self, gid: int):
        now = time.time()
        if now - self.cooldowns.get(gid, 0) < 2:
            return False
        self.cooldowns[gid] = now
        return True

    # =========================
    # CONNECT (STABLE CORE FIX)
    # =========================
    async def connect(self, guild: discord.Guild, channel: discord.VoiceChannel):
        gid = guild.id

        if not self._cooldown(gid):
            return "COOLDOWN"

        async with self._lock(gid):
            try:
                vc = guild.voice_client

                # =========================
                # STEP 1: SAFE CLEAN STATE
                # =========================
                if vc:
                    try:
                        if vc.is_connected():
                            if vc.channel.id == channel.id:
                                return True

                            await vc.disconnect()
                    except Exception:
                        pass

                    vc = None

                # IMPORTANT: allow Discord gateway reset
                await asyncio.sleep(2)

                # =========================
                # STEP 2: CONNECT RETRY LOOP
                # =========================
                for i in range(3):
                    try:
                        vc = await channel.connect(
                            timeout=20,
                            reconnect=True,
                            self_deaf=True
                        )

                        set_voice(gid, channel.id)
                        return True

                    except discord.ClientException:
                        # Edge case: already connected / stale session
                        vc = guild.voice_client
                        if vc and vc.is_connected():
                            return True

                        await asyncio.sleep(1)

                    except Exception as e:
                        print(f"[VOICE CONNECT RETRY {i+1}]", repr(e))
                        await asyncio.sleep(2 + i)

                return "CONNECT_FAILED"

            except Exception as e:
                print("[VOICE CONNECT FATAL]", repr(e))
                return "CONNECT_FAILED"

    # =========================
    # DISCONNECT
    # =========================
    async def disconnect(self, guild: discord.Guild):
        gid = guild.id

        async with self._lock(gid):
            try:
                vc = guild.voice_client

                if vc:
                    try:
                        await vc.disconnect()
                    except Exception:
                        pass

                remove_voice(gid)
                return True

            except Exception as e:
                print("[VOICE DISCONNECT ERROR]", repr(e))
                return "DISCONNECT_FAILED"

    # =========================
    # ENSURE CONNECTED (WATCHDOG)
    # =========================
    async def ensure_connected(self, guild: discord.Guild):
        gid = guild.id
        vc = guild.voice_client

        try:
            if vc and vc.is_connected():
                return

            data = self.bot.voice_manager_data if hasattr(self.bot, "voice_manager_data") else None
            if not data:
                return

        except Exception as e:
            print("[VOICE ENSURE ERROR]", repr(e))
