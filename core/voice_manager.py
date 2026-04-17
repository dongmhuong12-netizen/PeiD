import discord
import asyncio
import time
import traceback

from core.voice_storage import set_voice, remove_voice, get_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}
        self.cooldown = {}

    def _lock(self, gid):
        if gid not in self.locks:
            self.locks[gid] = asyncio.Lock()
        return self.locks[gid]

    def _cooldown_ok(self, gid):
        now = time.time()
        if now - self.cooldown.get(gid, 0) < 2:
            return False
        self.cooldown[gid] = now
        return True

    async def connect(self, guild: discord.Guild, channel: discord.VoiceChannel):
        gid = guild.id

        if not self._cooldown_ok(gid):
            return "COOLDOWN"

        async with self._lock(gid):
            vc = guild.voice_client

            if vc and vc.is_connected() and vc.channel.id == channel.id:
                return True

            for i in range(3):
                try:
                    if vc and vc.is_connected():
                        await vc.move_to(channel)
                    else:
                        await channel.connect(self_deaf=True)

                    set_voice(gid, channel.id)
                    return True

                except Exception as e:
                    print(f"[VOICE CONNECT FAIL {i+1}]", repr(e))
                    traceback.print_exc()
                    await asyncio.sleep(1.5)

            return "CONNECT_FAILED"

    async def disconnect(self, guild: discord.Guild):
        gid = guild.id

        async with self._lock(gid):
            vc = guild.voice_client

            try:
                if vc and vc.is_connected():
                    await vc.disconnect()

                remove_voice(gid)
                return True

            except Exception as e:
                print("[VOICE DISCONNECT ERROR]", repr(e))
                traceback.print_exc()
                return "DISCONNECT_FAILED"

    async def ensure_connected(self, guild: discord.Guild):
        data = get_voice(guild.id)
        if not data or not data.get("channel_id"):
            return

        channel = guild.get_channel(data["channel_id"])
        if not channel:
            remove_voice(guild.id)
            return

        vc = guild.voice_client
        if not vc or not vc.is_connected():
            try:
                await channel.connect(self_deaf=True)
            except Exception as e:
                print("[VOICE RESTORE FAIL]", repr(e))
