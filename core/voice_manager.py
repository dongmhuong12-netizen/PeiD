import discord
import asyncio
import time
from core.voice_storage import set_voice, remove_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot

        self.locks = {}
        self.cooldowns = {}
        self.sessions = {}  # guild_id -> session state

    # =========================
    # LOCK
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
    # CONNECT
    # =========================
    async def connect(self, guild: discord.Guild, channel: discord.VoiceChannel):
        gid = guild.id

        if not self._cooldown(gid):
            return "COOLDOWN"

        async with self._lock(gid):
            try:
                vc = guild.voice_client

                # already connected
                if vc and vc.is_connected():
                    if vc.channel.id == channel.id:
                        self._set_session(gid, channel.id, "CONNECTED")
                        return True
                    await vc.move_to(channel)
                else:
                    await channel.connect(self_deaf=True)

                set_voice(gid, channel.id)
                self._set_session(gid, channel.id, "CONNECTED")

                return True

            except Exception as e:
                print("[VOICE CONNECT ERROR]", repr(e))
                self._set_session(gid, None, "FAILED", str(e))
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
                    await vc.disconnect()

                remove_voice(gid)
                self._set_session(gid, None, "DISCONNECTED")

                return True

            except Exception as e:
                print("[VOICE DISCONNECT ERROR]", repr(e))
                return "DISCONNECT_FAILED"

    # =========================
    # ENSURE CONNECTED (WATCHDOG CORE)
    # =========================
    async def ensure_connected(self, guild: discord.Guild):
        gid = guild.id
        session = self.sessions.get(gid)

        if not session:
            return

        if session["state"] == "DISCONNECTED":
            return

        channel_id = session.get("channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        vc = guild.voice_client

        try:
            if not vc or not vc.is_connected():
                await channel.connect(self_deaf=True)
                self._set_session(gid, channel_id, "CONNECTED")

        except Exception as e:
            print("[VOICE ENSURE ERROR]", repr(e))

    # =========================
    # SESSION UPDATE
    # =========================
    def _set_session(self, gid, channel_id, state, error=None):
        self.sessions[gid] = {
            "channel_id": channel_id,
            "state": state,
            "error": error,
            "updated": time.time()
        }
