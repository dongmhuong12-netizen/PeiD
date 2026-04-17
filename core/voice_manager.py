import discord
import asyncio
import time
import traceback

from core.voice_storage import set_voice, remove_voice, get_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.guild_locks = {}
        self.cooldown = {}

    def _lock(self, gid):
        if gid not in self.guild_locks:
            self.guild_locks[gid] = asyncio.Lock()
        return self.guild_locks[gid]

    def _cooldown(self, gid):
        now = time.time()
        if now - self.cooldown.get(gid, 0) < 3:
            return False
        self.cooldown[gid] = now
        return True

    # =========================
    # JOIN (HARD STABLE)
    # =========================
    async def join(self, interaction, channel: discord.VoiceChannel):
        guild = interaction.guild
        gid = guild.id

        if not self._cooldown(gid):
            return "COOLDOWN"

        async with self._lock(gid):

            try:
                vc = guild.voice_client

                # already in channel
                if vc and vc.is_connected():
                    if vc.channel.id == channel.id:
                        return True
                    await vc.move_to(channel)
                    return True

                # 🔥 HARD STABILIZER
                await asyncio.sleep(1.5)

                for i in range(3):
                    try:
                        vc = await channel.connect(
                            timeout=20,
                            reconnect=True,
                            self_deaf=True
                        )

                        set_voice(gid, channel.id)
                        return True

                    except Exception as e:
                        print(f"[VOICE TRY {i+1}]", repr(e))
                        await asyncio.sleep(2 + i * 2)

                return "CONNECT_FAILED"

            except Exception as e:
                print("[VOICE JOIN FATAL]", repr(e))
                traceback.print_exc()
                return "CONNECT_FAILED"

    # =========================
    async def leave(self, guild, manual=True):
        gid = guild.id

        async with self._lock(gid):
            try:
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()

                remove_voice(gid)
                return True

            except Exception as e:
                print("[VOICE LEAVE]", repr(e))
                return "LEAVE_FAILED"
