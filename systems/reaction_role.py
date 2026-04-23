import discord
from discord.ext import commands
import asyncio
from collections import defaultdict

from core.cache_manager import load, mark_dirty
from core.state import State

FILE_KEY = "reaction_roles"

# Lock theo User để đảm bảo thứ tự xử lý nhưng không gây chậm toàn cục
_user_locks = defaultdict(asyncio.Lock)

def _normalize_emoji(e) -> str:
    return str(e).strip()

# =========================
# CORE COG
# =========================

class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load(FILE_KEY) or {}
        self.emoji_map = {} 
        # Cache tin nhắn để tránh fetch_message liên tục gây chậm
        self.msg_obj_cache = {}

    def _refresh(self):
        self.data = load(FILE_KEY) or {}
        self.build_cache()

    @commands.Cog.listener()
    async def on_ready(self):
        self._refresh()
        print("ReactionRole SPEED PATCH LOADED")

    def build_cache(self):
        self.emoji_map.clear()
        for msg_id, config in self.data.items():
            msg_id = str(msg_id)
            self.emoji_map[msg_id] = {}
            for group in config.get("groups", []):
                mode = group.get("mode", "multi")
                emojis = [_normalize_emoji(e) for e in group.get("emojis", [])]
                roles = [str(r) for r in group.get("roles", [])]
                for i in range(len(emojis)):
                    if i < len(roles):
                        self.emoji_map[msg_id][emojis[i]] = {
                            "target_role": roles[i],
                            "mode": mode,
                            "group_roles": roles,
                            "group_emojis": emojis
                        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        
        emoji = _normalize_emoji(payload.emoji)
        msg_id = str(payload.message_id)
        
        if msg_id not in self.emoji_map:
            self._refresh()
            if msg_id not in self.emoji_map: return
        if emoji not in self.emoji_map[msg_id]: return

        # Xử lý tuần tự cho từng User nhưng không đợi 60s
        async with _user_locks[payload.user_id]:
            guild = self.bot.get_guild(payload.guild_id)
            member = payload.member or guild.get_member(payload.user_id)
            if not member or member.bot: return

            data = self.emoji_map[msg_id][emoji]
            target_role_id = int(data["target_role"])
            target_role = guild.get_role(target_role_id)
            if not target_role: return

            # Nếu là Single Mode
            if data["mode"] == "single":
                tasks = []
                
                # 1. Gom role cũ cần xóa
                roles_to_remove = [
                    guild.get_role(int(rid)) for rid in data["group_roles"] 
                    if int(rid) != target_role_id
                ]
                to_rem = [r for r in roles_to_remove if r and r in member.roles]
                if to_rem:
                    tasks.append(member.remove_roles(*to_rem))

                # 2. Gỡ Reaction cũ (UI Sync)
                try:
                    # Lấy message từ cache hoặc fetch nếu cần
                    message = self.msg_obj_cache.get(msg_id)
                    if not message:
                        channel = self.bot.get_channel(payload.channel_id)
                        message = await channel.fetch_message(payload.message_id)
                        self.msg_obj_cache[msg_id] = message

                    for r in message.reactions:
                        r_emo = _normalize_emoji(r.emoji)
                        if r_emo in data["group_emojis"] and r_emo != emoji:
                            tasks.append(r.remove(member))
                except: pass

                # Thực hiện dọn dẹp song song
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            # 3. Gán Role mới ngay lập tức
            if target_role not in member.roles:
                await member.add_roles(target_role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        msg_id = str(payload.message_id)
        if msg_id not in self.emoji_map: return
        emoji = _normalize_emoji(payload.emoji)
        if emoji not in self.emoji_map[msg_id]: return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        data = self.emoji_map[msg_id][emoji]
        role = guild.get_role(int(data["target_role"]))
        
        if role and role in member.roles:
            await member.remove_roles(role)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
