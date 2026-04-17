import discord
import asyncio
import time

from core.voice_storage import set_voice, remove_voice, get_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}
        self.cooldowns = {}
        self.sessions = {}  # RAM state

    def _lock(self, gid: int):
        if gid not in self.locks:
            self.locks[gid] = asyncio.Lock()
        return self.locks[gid]

    def _cooldown(self, gid: int):
        now = time.time()
        if now - self.cooldowns.get(gid, 0) < 2:
            return False
        self.cooldowns[gid] = now
        return True

    # =========================
    # CONNECT
    # =========================
    async def connect(self, guild: discord.Guild, channel: discord.VoiceChannel):
        gid = guild.id

        if not self._cooldown(gid):
            return "COOLDOWN"

        async with self._lock(gid):
            try:
                vc = guild.voice_client

                # already correct
                if vc and vc.is_connected():
                    if vc.channel.id == channel.id:
                        self.sessions[gid] = channel.id
                        return True
                    await vc.move_to(channel)
                    self.sessions[gid] = channel.id
                    set_voice(gid, channel.id)
                    return True

                # clean stale
                if vc:
                    try:
                        await vc.disconnect(force=True)
                    except:
                        pass

                await asyncio.sleep(2)

                vc = await channel.connect(self_deaf=True)

                self.sessions[gid] = channel.id
                set_voice(gid, channel.id)

                return True

            except Exception as e:
                print("[VOICE CONNECT ERROR]", repr(e))
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
                    await vc.disconnect(force=True)

                self.sessions.pop(gid, None)

                # 🔥 mark manual leave
                set_voice(gid, None, manual=True)

                return True

            except Exception as e:
                print("[VOICE DISCONNECT ERROR]", repr(e))
                return "DISCONNECT_FAILED"

    # =========================
    # ENSURE CONNECTED (ONLY SERVICE USE)
    # =========================
    async def ensure(self, guild: discord.Guild):
        gid = guild.id

        data = get_voice(gid)
        if not data:
            return

        if data.get("manual_leave"):
            return

        channel_id = data.get("channel_id")
        if not channel_id:
            return

        vc = guild.voice_client

        if vc and vc.is_connected():
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        try:
            await asyncio.sleep(1)
            await channel.connect(self_deaf=True)
            self.sessions[gid] = channel_id

            print(f"[VOICE RECOVERED] {gid}")

        except Exception as e:
            print("[VOICE ENSURE ERROR]", repr(e))
