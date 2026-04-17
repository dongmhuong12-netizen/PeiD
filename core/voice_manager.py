import discord
import asyncio
import time
from core.voice_storage import set_voice, remove_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}
        self.sessions = {}  # guild_id -> channel_id

    def _lock(self, gid):
        if gid not in self.locks:
            self.locks[gid] = asyncio.Lock()
        return self.locks[gid]

    # =========================
    # CONNECT (CORE SAFE MODE)
    # =========================
    async def connect(self, guild: discord.Guild, channel: discord.VoiceChannel):
        gid = guild.id

        async with self._lock(gid):
            try:
                vc = guild.voice_client

                # already connected
                if vc and vc.is_connected():
                    if vc.channel.id == channel.id:
                        return True
                    await vc.move_to(channel)
                    self.sessions[gid] = channel.id
                    return True

                # CLEAN OLD STATE (IMPORTANT FIX)
                if vc:
                    try:
                        await vc.disconnect(force=True)
                    except:
                        pass

                await asyncio.sleep(1.2)

                # CONNECT SAFE
                vc = await channel.connect(
                    self_deaf=True,
                    reconnect=True
                )

                self.sessions[gid] = channel.id
                set_voice(gid, channel.id)

                return True

            except discord.ClientException:
                # fallback: already connected somewhere
                vc = guild.voice_client
                if vc and vc.is_connected():
                    await vc.move_to(channel)
                    self.sessions[gid] = channel.id
                    return True

                return "ALREADY_CONNECTED_ERROR"

            except Exception as e:
                print("[VOICE CONNECT ERROR]", repr(e))
                return "CONNECT_FAILED"

    # =========================
    # DISCONNECT SAFE
    # =========================
    async def disconnect(self, guild: discord.Guild):
        gid = guild.id

        async with self._lock(gid):
            vc = guild.voice_client

            if vc and vc.is_connected():
                try:
                    await vc.disconnect(force=True)
                except:
                    pass

            self.sessions.pop(gid, None)
            remove_voice(gid)

            return True

    # =========================
    # WATCHDOG RECOVERY
    # =========================
    async def ensure_connected(self, guild: discord.Guild):
        gid = guild.id

        if gid not in self.sessions:
            return

        channel_id = self.sessions[gid]
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        vc = guild.voice_client

        try:
            if not vc or not vc.is_connected():
                await channel.connect(self_deaf=True)
        except:
            pass
