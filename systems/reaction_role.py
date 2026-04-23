import discord
from discord.ext import commands
import asyncio
import time
from collections import deque

from core.cache_manager import load, mark_dirty
from core.state import State

FILE_KEY = "reaction_roles"

# =========================
# EVENT DEDUP (Giữ nguyên logic của Nguyệt)
# =========================

EVENT_TTL = 60
_event_log = deque()
_event_set = set()
_event_lock = asyncio.Lock()

def _cleanup_events():
    now = time.time()
    while _event_log:
        if now - _event_log[0][0] <= EVENT_TTL:
            break
        _, key = _event_log.popleft()
        _event_set.discard(key)

async def _is_duplicate(key: str):
    async with _event_lock:
        _cleanup_events()
        return key in _event_set

async def _mark_event(key: str):
    async with _event_lock:
        _cleanup_events()
        _event_set.add(key)
        _event_log.append((time.time(), key))

# =========================
# NORMALIZER
# =========================

def _normalize_emoji(e) -> str:
    return str(e).strip()

def _emoji_key(payload_emoji) -> str:
    return _normalize_emoji(payload_emoji)

def _normalize_roles(roles):
    if isinstance(roles, list):
        return [str(r) for r in roles]
    return [str(roles)]

# =========================
# CORE COG
# =========================

class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load(FILE_KEY) or {}
        self.emoji_map = {} 
        self.message_cache = {}
        self._cache_limit = 200

    def _refresh(self):
        self.data = load(FILE_KEY) or {}
        self.build_cache()

    @commands.Cog.listener()
    async def on_ready(self):
        self._refresh()
        print("ReactionRole SAFE PATCH LOADED")

    def build_cache(self):
        self.emoji_map.clear()
        for msg_id, config in self.data.items():
            msg_id = str(msg_id)
            self.emoji_map[msg_id] = {}

            for group in config.get("groups", []):
                mode = group.get("mode", "multi")
                emojis = [_normalize_emoji(e) for e in group.get("emojis", [])]
                roles = _normalize_roles(group.get("roles", []))

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
        if not payload.guild_id: return

        emoji = _emoji_key(payload.emoji)
        key = f"{payload.user_id}:{payload.message_id}:{emoji}"
        
        if await _is_duplicate(key): return
        await _mark_event(key)

        msg_id = str(payload.message_id)
        if msg_id not in self.emoji_map:
            self._refresh()
            if msg_id not in self.emoji_map: return

        if emoji not in self.emoji_map[msg_id]: return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        data = self.emoji_map[msg_id][emoji]
        target_role_id = int(data["target_role"])
        target_role = guild.get_role(target_role_id)
        if not target_role: return

        # --- LOGIC FIX LỖI SINGLE (Quy tắc 5: Cưỡng ép dọn dẹp) ---
        if data["mode"] == "single":
            cleanup_tasks = []
            
            # 1. Gom danh sách Role cũ cần xóa
            roles_to_remove = []
            for r_id in data["group_roles"]:
                if int(r_id) == target_role_id: continue
                r_obj = guild.get_role(int(r_id))
                if r_obj and r_obj in member.roles:
                    roles_to_remove.append(r_obj)
            
            if roles_to_remove:
                cleanup_tasks.append(member.remove_roles(*roles_to_remove))

            # 2. Gom danh sách Reaction cũ cần gỡ (UI Sync)
            try:
                channel = self.bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                for r in message.reactions:
                    r_emo = _normalize_emoji(r.emoji)
                    if r_emo in data["group_emojis"] and r_emo != emoji:
                        cleanup_tasks.append(r.remove(member))
            except: pass

            # Chạy song song tất cả các lệnh gỡ để đảm bảo tốc độ cực nhanh
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # 3. Gán Role mới (Sau khi đã dọn dẹp hoặc chạy song song)
        if target_role not in member.roles:
            await member.add_roles(target_role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id: return

        msg_id = str(payload.message_id)
        if msg_id not in self.emoji_map:
            self._refresh()
            if msg_id not in self.emoji_map: return

        emoji = _emoji_key(payload.emoji)
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
