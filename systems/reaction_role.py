import discord
from discord.ext import commands
import asyncio
from collections import defaultdict

from core.cache_manager import get_raw, load
from core.state import State

FILE_KEY = "reaction_roles"

# Lock theo User để tránh Race Condition khi nhấn liên tục (Tiêu chuẩn 100k+)
_user_locks = defaultdict(asyncio.Lock)

def _normalize_emoji(e) -> str:
    return str(e).strip()

# =========================
# CORE COG: REACTION SYSTEM
# =========================

class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emoji_map = {} 
        # Không dùng cache message vĩnh viễn để bảo vệ RAM

    def _refresh_cache(self):
        """Đồng bộ dữ liệu từ RAM CacheManager vào bản đồ Emoji"""
        data = get_raw(FILE_KEY) or {}
        self.emoji_map.clear()
        
        for msg_id, config in data.items():
            # Chỉ xử lý các key là ID tin nhắn (đã được sender/ui đăng ký)
            if not msg_id.isdigit(): continue
            
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
    async def on_ready(self):
        self._refresh_cache()
        print(f"🚀 [SYSTEM] ReactionRole: Đã nạp {len(self.emoji_map)} bản đồ phản xạ.", flush=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        
        msg_id = str(payload.message_id)
        emoji = _normalize_emoji(payload.emoji)
        
        # 1. Cơ chế Tự động tỉnh thức (Auto-Sync)
        if msg_id not in self.emoji_map:
            # Kiểm tra xem ID này có trong não bộ State không
            if await State.get_info_by_mid(msg_id):
                self._refresh_cache() # Nạp lại toàn bộ để cập nhật tin nhắn mới
            
        if msg_id not in self.emoji_map or emoji not in self.emoji_map[msg_id]:
            return

        # 2. Xử lý tuần tự cho từng User
        async with _user_locks[payload.user_id]:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild: return
            
            member = payload.member or guild.get_member(payload.user_id)
            if not member or member.bot: return

            config = self.emoji_map[msg_id][emoji]
            target_role = guild.get_role(int(config["target_role"]))
            if not target_role: return

            # THỰC THI GÁN ROLE
            if target_role not in member.roles:
                try:
                    await member.add_roles(target_role, reason="PeiD Reaction Role: Added")
                except discord.Forbidden:
                    print(f"[ERROR] Thiếu quyền gán role tại Guild {guild.id}", flush=True)
                except Exception: pass

            # Xử lý Single Mode (Chỉ được chọn 1)
            if config["mode"] == "single":
                asyncio.create_task(self._handle_single_mode(payload, config, member, target_role.id))

    async def _handle_single_mode(self, payload, config, member, current_role_id):
        """Dọn dẹp các role và reaction thừa (Background Task)"""
        guild = member.guild
        
        # Gỡ các role khác trong cùng Group
        roles_to_remove = [
            guild.get_role(int(rid)) for rid in config["group_roles"] 
            if int(rid) != current_role_id
        ]
        roles_to_remove = [r for r in roles_to_remove if r and r in member.roles]
        
        if roles_to_remove:
            try: await member.remove_roles(*roles_to_remove)
            except: pass

        # Gỡ Reaction cũ trên UI Discord
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            for r in message.reactions:
                e_str = _normalize_emoji(r.emoji)
                if e_str in config["group_emojis"] and e_str != _normalize_emoji(payload.emoji):
                    try:
                        await r.remove(member)
                        await asyncio.sleep(0.2) # Chống Rate Limit
                    except: pass
        except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        msg_id = str(payload.message_id)
        emoji = _normalize_emoji(payload.emoji)
        
        if msg_id not in self.emoji_map or emoji not in self.emoji_map[msg_id]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        config = self.emoji_map[msg_id][emoji]
        # Chỉ gỡ role nếu ở chế độ Multi (Single mode thường gỡ bằng tay hoặc giữ nguyên)
        role = guild.get_role(int(config["target_role"]))
        
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="PeiD Reaction Role: Removed")
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
