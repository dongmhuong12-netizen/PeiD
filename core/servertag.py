import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict

from core.servertag_storage import (
    get_servertag_config, update_servertag_config,
    get_user_servertag_state, update_user_servertag_state
)
from core.embed_storage import load_embed
from core.variable_engine import apply_variables
from utils.emojis import Emojis

_config_locks = defaultdict(asyncio.Lock)

async def _embed_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        from core.embed_storage import list_embeds
        embed_list = await list_embeds(interaction.guild_id)
        return [app_commands.Choice(name=name, value=name) for name in embed_list if current.lower() in name.lower()][:25]
    except Exception:
        return []

async def send_servertag_message(bot, guild: discord.Guild, member: discord.Member) -> bool:
    config = await get_servertag_config(bot, guild.id)
    if not config: return False

    channel_id = config.get("channel_id")
    message_text = config.get("message")
    embed_name = config.get("embed_name")

    if not channel_id: return False
    channel = guild.get_channel(int(channel_id))
    if not channel: return False

    perms = channel.permissions_for(guild.me)
    if not perms.send_messages: return False

    ninja_mode = {"silent": True, "allowed_mentions": discord.AllowedMentions(users=False)}

    try:
        final_content = apply_variables(message_text, guild, member) if message_text else None
        final_embed = None

        if embed_name and perms.embed_links:
            embed_data = await load_embed(guild.id, embed_name)
            if embed_data:
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed, **ninja_mode)
            return True
        return False
    except Exception as e:
        print(f"[SERVER TAG ERROR] Thất bại tại guild {guild.id}: {e}", flush=True)
        return False

# ======================
# COMMAND GROUPS
# ======================

class ServerTagGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="servertag", description="Cấu hình hệ thống tự động gán vai trò khi treo trạng thái hoặc thẻ máy chủ")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_servertag_config(interaction.client, gid, "channel_id", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình kênh thông báo thành công: {channel.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="trigger", description="Thiết lập từ khóa yêu cầu treo trên Trạng thái tùy chỉnh")
    @app_commands.default_permissions(manage_guild=True)
    async def trigger(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_servertag_config(interaction.client, gid, "trigger_status", keyword)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cài đặt từ khóa trạng thái thành công: `{keyword}`", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="role", description="Cài đặt Vai trò thưởng khi thành viên đáp ứng đủ điều kiện tag")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_servertag_config(interaction.client, gid, "reward_role_id", role.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình vai trò phần thưởng thành công: {role.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn văn bản cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_servertag_config(interaction.client, gid, "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        display_msg = apply_variables(message, interaction.guild, interaction.user)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cập nhật văn bản thông báo thành công: {display_msg}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="Gán khối hình embed thiết kế mẫu")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(title=f"{Emojis.HOICHAM} Không tìm thấy mẫu thiết kế `{name}`", description="Vui lòng kiểm tra lại cấu hình mẫu.", color=0xe6e2dd)
            return await interaction.followup.send(embed=embed_err)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            await update_servertag_config(interaction.client, gid, "embed_name", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed_success = discord.Embed(title=f"{Emojis.BUOMA} Cập nhật mẫu thiết kế `{name}` thành công", color=0xe6e2dd)
        await interaction.followup.send(embed=embed_success)

    @embed.autocomplete('name')
    async def embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    @app_commands.command(name="test", description="Giả lập gửi thử nghiệm cấu trúc thông báo")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_servertag_message(interaction.client, interaction.guild, interaction.user)
        if success:
            embed = discord.Embed(title=f"{Emojis.BUOMA} Kiểm tra cấu trúc phân phát thành công", color=0xe6e2dd)
        else:
            embed = discord.Embed(title=f"{Emojis.HOICHAM} Cấu hình rỗng hoặc thiếu điều kiện nạp dữ liệu", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)


# ======================
# LISTENER & GATEWAY SCANNER
# ======================

class ServerTagListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = set()

    def cog_unload(self):
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_socket_response(self, payload: dict):
        event_name = payload.get("t")
        if event_name not in ["PRESENCE_UPDATE", "GUILD_MEMBER_UPDATE"]:
            return

        data = payload.get("d", {})
        if not data: return
        
        try:
            guild_id = int(data.get("guild_id", 0))
            user_data = data.get("user", {})
            user_id = int(user_data.get("id", 0))
        except (TypeError, ValueError):
            return

        # [FIX]: Ép kiểu an toàn 'is True' để tránh lỗi lọc nhầm ở PRESENCE_UPDATE
        if not guild_id or not user_id or user_data.get("bot") is True:
            return

        config = await get_servertag_config(self.bot, guild_id)
        trigger_status = config.get("trigger_status")
        reward_role_id = config.get("reward_role_id")

        # Lấy trạng thái lưu trữ quá khứ từ Database
        cached_state = await get_user_servertag_state(self.bot, guild_id, user_id)
        
        new_has_clan = cached_state["has_clan"]
        new_has_status = cached_state["has_status"]
        db_updates = {}

        # 1. ĐÁNH GIÁ THẺ MÁY CHỦ (CLAN TAG) NẾU XUẤT HIỆN TRONG PAYLOAD
        if "primary_guild" in user_data:
            pg = user_data["primary_guild"]
            if pg:
                enabled = pg.get("identity_enabled", True)
                clan_id = pg.get("identity_guild_id") or pg.get("id")
                current_tag_valid = (enabled and str(clan_id) == str(guild_id))
            else:
                current_tag_valid = False
            
            if current_tag_valid != cached_state["has_clan"]:
                new_has_clan = current_tag_valid
                db_updates["has_clan"] = new_has_clan

        # 2. ĐÁNH GIÁ TRẠNG THÁI (CUSTOM STATUS) NẾU XUẤT HIỆN TRONG PAYLOAD
        # [FIX]: Loại bỏ điều kiện 'in data' nguy hiểm. Bắt buộc kiểm tra lại nếu có trigger_status
        if trigger_status and event_name == "PRESENCE_UPDATE":
            activities = data.get("activities", [])
            current_status_valid = False
            for act in activities:
                if act.get("type") == 4:
                    state_text = str(act.get("state", "")).lower()
                    if trigger_status.lower() in state_text:
                        current_status_valid = True
                        break
            
            if current_status_valid != cached_state["has_status"]:
                new_has_status = current_status_valid
                db_updates["has_status"] = new_has_status

        # Tính toán điều kiện hợp lệ tổng hợp
        is_eligible = (new_has_clan or new_has_status)
        was_rewarded = cached_state["is_rewarded"]

        # Nếu không có hành động phân phát nhưng trạng thái thô thay đổi -> Cập nhật bộ nhớ đệm ẩn
        if (not is_eligible and not was_rewarded) or (is_eligible and was_rewarded):
            if db_updates:
                await update_user_servertag_state(self.bot, guild_id, user_id, db_updates)
            return  # Thoát sớm để tránh hao tổn tài nguyên

        # 3. CHU TRÌNH THỰC THI CHÍNH XÁC TUYỆT ĐỐI
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        
        member = guild.get_member(user_id)
        if not member:
            # [FIX]: Chỉ gọi API fetch_member đắt đỏ khi chắc chắn cần gán/gỡ Role, chống Rate Limit
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return

        reward_role = guild.get_role(int(reward_role_id)) if reward_role_id else None
        
        # TRƯỜNG HỢP A: Kích hoạt phần thưởng mới
        if is_eligible and not was_rewarded:
            db_updates["is_rewarded"] = True
            await update_user_servertag_state(self.bot, guild_id, user_id, db_updates)
            
            if reward_role and reward_role not in member.roles:
                try:
                    await member.add_roles(reward_role, reason="Hệ thống Servertag: Bật trạng thái hợp lệ")
                except Exception: pass
            
            task = asyncio.create_task(send_servertag_message(self.bot, guild, member))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        # TRƯỜNG HỢP B: Thu hồi toàn bộ quyền lợi và xóa vết
        elif not is_eligible and was_rewarded:
            db_updates["is_rewarded"] = False
            await update_user_servertag_state(self.bot, guild_id, user_id, db_updates)
            
            if reward_role and reward_role in member.roles:
                try:
                    await member.remove_roles(reward_role, reason="Hệ thống Servertag: Tắt trạng thái hợp lệ")
                except Exception: pass

async def setup(bot: commands.Bot):
    bot.tree.add_command(ServerTagGroup())
    await bot.add_cog(ServerTagListener(bot))
    print("[load] success: core.servertag (Ma trận trạng thái an toàn Gateway)", flush=True)
