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
        # Sử dụng cache hữu hạn hoặc fetch trực tiếp để tránh Memory Leak (100k servers)
        self.msg_obj_cache = {} 

    def _refresh(self):
        self.data = load(FILE_KEY) or {}
        self.build_cache()

    @commands.Cog.listener()
    async def on_ready(self):
        self._refresh()
        print("🚀 ReactionRole: Hệ phản xạ 100k+ READY")

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
        
        # 1. Kiểm tra cache Cog
        if msg_id not in self.emoji_map:
            # 2. Check "não bộ" bền vững (Fix lỗi mất trí nhớ sau restart)
            info = await State.get_info_by_mid(msg_id)
            if not info: 
                # Thử refresh lần cuối nếu file vừa được lưu
                self._refresh()
                if msg_id not in self.emoji_map: return
            
        if emoji not in self.emoji_map.get(msg_id, {}): return

        # Xử lý tuần tự cho từng User (Tránh Race Condition)
        async with _user_locks[payload.user_id]:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild: return
            member = payload.member or guild.get_member(payload.user_id)
            if not member or member.bot: return

            data = self.emoji_map[msg_id][emoji]
            target_role_id = int(data["target_role"])
            target_role = guild.get_role(target_role_id)
            if not target_role: return

            # XỬ LÝ GÁN ROLE TRƯỚC (Ưu tiên tốc độ phản hồi cho User)
            if target_role not in member.roles:
                try:
                    await member.add_roles(target_role, reason="Reaction Role: Assigned")
                except Exception: pass

            # XỬ LÝ DỌN DẸP UI (Chế độ Single Mode)
            if data["mode"] == "single":
                # Đưa việc xóa reaction vào background task để không làm nghẽn luồng gán role
                asyncio.create_task(self._handle_single_mode_cleanup(payload, data, member, target_role_id))

    async def _handle_single_mode_cleanup(self, payload, data, member, target_role_id):
        """Xử lý gỡ role cũ và reaction cũ một cách an toàn (Chống Rate Limit)"""
        guild = self.bot.get_guild(payload.guild_id)
        
        # 1. Gỡ các role khác trong cùng group
        roles_to_remove = []
        for rid in data["group_roles"]:
            rid_int = int(rid)
            if rid_int != target_role_id:
                r = guild.get_role(rid_int)
                if r and r in member.roles:
                    roles_to_remove.append(r)
        
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Reaction Role: Single Mode Sync")
            except: pass

        # 2. Gỡ Reaction cũ trên UI (Silent Task)
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = self.msg_obj_cache.get(str(payload.message_id))
            if not message:
                message = await channel.fetch_message(payload.message_id)
                # Chỉ cache ngắn hạn để tránh rò rỉ RAM
                self.msg_obj_cache[str(payload.message_id)] = message
                
            for r in message.reactions:
                r_emo = _normalize_emoji(r.emoji)
                if r_emo in data["group_emojis"] and r_emo != _normalize_emoji(payload.emoji):
                    try:
                        await r.remove(member)
                        await asyncio.sleep(0.2) # Delay nhẹ chống Rate Limit API Discord
                    except: pass
        except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        msg_id = str(payload.message_id)
        if msg_id not in self.emoji_map: return
        emoji = _normalize_emoji(payload.emoji)
        if emoji not in self.emoji_map[msg_id]: return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        data = self.emoji_map[msg_id][emoji]
        role = guild.get_role(int(data["target_role"]))
        
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Reaction Role: Removed")
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
