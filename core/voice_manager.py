import discord
import asyncio
import time
from core.voice_storage import set_voice, remove_voice, get_voice


class VoiceManager:
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()
        self.guild_locks = {}
        self.last_controller = {}
        self.cooldown = {}

    def _can_run(self, guild_id: int):
        now = time.time()
        if now - self.cooldown.get(guild_id, 0) < 5:
            return False
        self.cooldown[guild_id] = now
        return True

    def _get_lock(self, guild_id: int):
        if guild_id not in self.guild_locks:
            self.guild_locks[guild_id] = asyncio.Lock()
        return self.guild_locks[guild_id]

    async def join(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        guild = interaction.guild
        gid = guild.id

        if not self._can_run(gid):
            return "COOLDOWN"

        async with self._get_lock(gid):
            try:
                vc = guild.voice_client

                if vc and vc.is_connected():
                    await vc.move_to(channel)
                else:
                    await channel.connect()

                set_voice(gid, channel.id)
                self.last_controller[gid] = interaction.user.id

                return True

            except Exception as e:
                return str(e)

    async def leave(self, guild: discord.Guild, manual=True):
        gid = guild.id

        async with self._get_lock(gid):
            try:
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()

                data = get_voice(gid)
                if data:
                    data["manual_leave"] = manual
                    data["enabled"] = False

                remove_voice(gid)
                return True

            except Exception as e:
                return str(e)

    async def restore_one(self, guild: discord.Guild, cfg: dict):
        gid = guild.id

        if not cfg.get("enabled", True):
            return

        if cfg.get("manual_leave"):
            return

        channel = guild.get_channel(cfg["channel_id"])
        if not channel:
            remove_voice(gid)
            return

        vc = guild.voice_client

        try:
            if not vc or not vc.is_connected():
                await channel.connect()

        except Exception as e:
            cfg["last_error"] = str(e)
            set_voice(gid, cfg["channel_id"])

    async def restore_all(self):
        from core.voice_storage import get_all

        data = get_all()

        for gid, cfg in data.items():
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue

            await self.restore_one(guild, cfg)
