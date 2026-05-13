import discord
from discord.ext import commands
import asyncio
from collections import defaultdict

# Nạp công cụ Storage mới để truy xuất cấu hình từ MongoDB
from core.reaction_storage import get_reaction_config # [CẤY MỚI]
from utils.emojis import Emojis

# Lock theo User để tránh Race Condition khi nhấn liên tục (Tiêu chuẩn 100k+)
_user_locks = defaultdict(asyncio.Lock)
# [VÁ LỖI] Lock bảo vệ quá trình nạp dữ liệu tránh nạp chồng (Overlapping)
_refresh_lock = asyncio.Lock()

def _normalize_emoji(e) -> str:
    return str(e).strip()

# =========================
# CORE COG: REACTION SYSTEM
# =========================

class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # emoji_map sẽ được dùng làm Local Cache để truy xuất thần tốc (O(1))
        self.emoji_map = {} 

    async def _get_msg_config(self, guild_id: int, message_id: str):
        """
        [GIA CỐ] Mạch nạp trí nhớ linh hoạt.
        Nếu RAM chưa có, Bot sẽ tự động 'tỉnh thức' bằng cách nạp từ MongoDB.
        """
        if message_id not in self.emoji_map:
            async with _refresh_lock:
                # Kiểm tra lại lần nữa sau khi có Lock để tránh Double-Fetching
                if message_id not in self.emoji_map:
                    config = await get_reaction_config(guild_id, message_id)
                    if config:
                        self.emoji_map[message_id] = config
        return self.emoji_map.get(message_id)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"🚀 [SYSTEM] ReactionRole: Hệ thống đã sẵn sàng kết nối trí nhớ mới.", flush=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        
        msg_id = str(payload.message_id)
        emoji = _normalize_emoji(payload.emoji)
        
        # [KẾT NỐI MẠCH] Tự động lấy cấu hình từ Cloud nếu chưa có trong RAM
        msg_config = await self._get_msg_config(payload.guild_id, msg_id)
        if not msg_config or emoji not in msg_config:
            return

        # 2. Xử lý tuần tự cho từng User (Atomic Operations)
        lock = _user_locks[payload.user_id]
        async with lock:
            try:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild: return
                
                member = payload.member or guild.get_member(payload.user_id)
                if not member or member.bot: return

                config = msg_config[emoji]
                target_role = guild.get_role(int(config["target_role"]))
                if not target_role: return

                # THỰC THI GÁN ROLE
                if target_role not in member.roles:
                    try:
                        await member.add_roles(target_role, reason="PeiD Reaction Role: Added")
                    except discord.Forbidden:
                        print(f"[ERROR] Thiếu quyền gán role tại Guild {guild.id}", flush=True)
                    except Exception: pass

                # Xử lý Single Mode (Chỉ được chọn 1 trong nhóm)
                if config.get("mode") == "single":
                    asyncio.create_task(self._handle_single_mode(payload, config, member, target_role.id))
            finally:
                # [VÁ LỖI] Dọn dẹp RAM: Xóa Lock khỏi bộ nhớ nếu không còn tác vụ nào chờ
                if payload.user_id in _user_locks and not lock.locked():
                    _user_locks.pop(payload.user_id, None)

    async def _handle_single_mode(self, payload, config, member, current_role_id):
        """Dọn dẹp các role và reaction thừa (Background Task)"""
        guild = member.guild
        
        # Gỡ các role khác trong cùng Group
        group_roles = config.get("group_roles", [])
        roles_to_remove = [
            guild.get_role(int(rid)) for rid in group_roles 
            if int(rid) != current_role_id
        ]
        roles_to_remove = [r for r in roles_to_remove if r and r in member.roles]
        
        if roles_to_remove:
            try: await member.remove_roles(*roles_to_remove)
            except: pass

        # Gỡ Reaction cũ trên UI Discord để đồng bộ trạng thái
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel: channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            group_emojis = config.get("group_emojis", [])
            for r in message.reactions:
                e_str = _normalize_emoji(r.emoji)
                if e_str in group_emojis and e_str != _normalize_emoji(payload.emoji):
                    try:
                        await r.remove(member)
                        await asyncio.sleep(0.2) # Chống Rate Limit (Industrial Standard)
                    except: pass
        except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        msg_id = str(payload.message_id)
        emoji = _normalize_emoji(payload.emoji)
        
        # [KẾT NỐI MẠCH] Nạp cấu hình từ Cloud nếu RAM bị trống sau khi Reboot
        msg_config = await self._get_msg_config(payload.guild_id, msg_id)
        if not msg_config or emoji not in msg_config:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        config = msg_config[emoji]
        # Chỉ gỡ role nếu ở chế độ Multi hoặc logic yêu cầu gỡ khi bỏ reaction
        role = guild.get_role(int(config["target_role"]))
        
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="PeiD Reaction Role: Removed")
            except: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
