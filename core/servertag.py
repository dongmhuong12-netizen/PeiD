import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict

from core.servertag_storage import (
    get_tag_config, update_tag_config,
    get_user_tag_state, update_user_tag_state
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

async def send_tag_message(bot, guild: discord.Guild, member: discord.Member, tag_type: str) -> bool:
    """Hàm gửi thông báo dùng chung, phân biệt qua tag_type ('status' hoặc 'clan')"""
    config = await get_tag_config(bot, guild.id, tag_type)
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
        print(f"[{tag_type.upper()} TAG ERROR] Thất bại tại guild {guild.id}: {e}", flush=True)
        return False

# ======================
# LỆNH: STATUS TAG (Trạng Thái)
# ======================

class StatusTagGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="statustag", description="Cấu hình hệ thống tự động gán vai trò khi treo Trạng thái tùy chỉnh")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "status", "channel_id", channel.id)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình kênh thông báo Status thành công: {channel.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="trigger", description="Thiết lập từ khóa yêu cầu treo trên Trạng thái tùy chỉnh")
    @app_commands.default_permissions(manage_guild=True)
    async def trigger(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "status", "trigger", keyword)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cài đặt từ khóa Status thành công: `{keyword}`", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="role", description="Cài đặt Vai trò thưởng khi thành viên đáp ứng đủ điều kiện Status")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "status", "reward_role_id", role.id)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình vai trò phần thưởng Status thành công: {role.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn văn bản cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "status", "message", message)
        display_msg = apply_variables(message, interaction.guild, interaction.user)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cập nhật văn bản thông báo Status thành công:\n{display_msg}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="Gán khối hình embed thiết kế mẫu")
    @app_commands.default_permissions(manage_guild=True)
    async def set_embed(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            return await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.HOICHAM} Không tìm thấy mẫu thiết kế `{name}`", color=0xe6e2dd))
        
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "status", "embed_name", name)
        await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.BUOMA} Cập nhật mẫu thiết kế Status `{name}` thành công", color=0xe6e2dd))

    @set_embed.autocomplete('name')
    async def set_embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    @app_commands.command(name="test", description="Giả lập gửi thử nghiệm cấu trúc thông báo Status")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_tag_message(interaction.client, interaction.guild, interaction.user, "status")
        if success:
            embed = discord.Embed(title=f"{Emojis.BUOMA} Kiểm tra cấu trúc phân phát Status thành công", color=0xe6e2dd)
        else:
            embed = discord.Embed(title=f"{Emojis.HOICHAM} Cấu hình rỗng hoặc kênh chưa được thiết lập", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)


# ======================
# LỆNH: CLAN TAG (Huy hiệu Máy chủ)
# ======================

class ClanTagGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="clantag", description="Cấu hình hệ thống tự động gán vai trò khi đeo Huy hiệu Máy chủ (Clan Tag)")

    @app_commands.command(name="channel", description="Đặt kênh gửi tin nhắn cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "clan", "channel_id", channel.id)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình kênh thông báo Clan Tag thành công: {channel.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="trigger", description="Thiết lập TỪ KHÓA (chữ) yêu cầu có trong Clan Tag")
    @app_commands.default_permissions(manage_guild=True)
    async def trigger(self, interaction: discord.Interaction, keyword: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "clan", "trigger", keyword)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cài đặt từ khóa Clan Tag thành công: `{keyword}`", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="role", description="Cài đặt Vai trò thưởng khi thành viên đeo đúng Clan Tag")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "clan", "reward_role_id", role.id)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cấu hình vai trò phần thưởng Clan Tag thành công: {role.mention}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="Đặt nội dung tin nhắn văn bản cảm ơn")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "clan", "message", message)
        display_msg = apply_variables(message, interaction.guild, interaction.user)
        embed = discord.Embed(title=f"{Emojis.BUOMA} Cập nhật văn bản thông báo Clan Tag thành công:\n{display_msg}", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="Gán khối hình embed thiết kế mẫu")
    @app_commands.default_permissions(manage_guild=True)
    async def set_embed(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            return await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.HOICHAM} Không tìm thấy mẫu thiết kế `{name}`", color=0xe6e2dd))
        
        gid = interaction.guild.id
        async with _config_locks[gid]:
            await update_tag_config(interaction.client, gid, "clan", "embed_name", name)
        await interaction.followup.send(embed=discord.Embed(title=f"{Emojis.BUOMA} Cập nhật mẫu thiết kế Clan Tag `{name}` thành công", color=0xe6e2dd))

    @set_embed.autocomplete('name')
    async def set_embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    @app_commands.command(name="test", description="Giả lập gửi thử nghiệm cấu trúc thông báo Clan Tag")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        success = await send_tag_message(interaction.client, interaction.guild, interaction.user, "clan")
        if success:
            embed = discord.Embed(title=f"{Emojis.BUOMA} Kiểm tra cấu trúc phân phát Clan Tag thành công", color=0xe6e2dd)
        else:
            embed = discord.Embed(title=f"{Emojis.HOICHAM} Cấu hình rỗng hoặc kênh chưa được thiết lập", color=0xe6e2dd)
        await interaction.followup.send(embed=embed)


# ======================
# LISTENER: BỘ NÃO KIỂM DUYỆT CHÉO (CROSS-VALIDATION)
# ======================

class ServerTagListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = set()

    def cog_unload(self):
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    # --- LÕI KIỂM DUYỆT CHÉO (CHỐNG XUNG ĐỘT ROLE) ---
    async def evaluate_member_tags(self, guild_id: int, user_id: int, tag_type: str, is_valid: bool):
        """
        tag_type: 'status' hoặc 'clan'
        is_valid: True nếu khớp từ khóa, False nếu không khớp
        """
        status_config = await get_tag_config(self.bot, guild_id, "status")
        clan_config = await get_tag_config(self.bot, guild_id, "clan")
        
        status_role_id = status_config.get("reward_role_id")
        clan_role_id = clan_config.get("reward_role_id")
        
        cached_state = await get_user_tag_state(self.bot, guild_id, user_id)
        
        has_status = is_valid if tag_type == "status" else cached_state["has_status"]
        has_clan = is_valid if tag_type == "clan" else cached_state["has_clan"]
        
        status_rewarded = cached_state["status_rewarded"]
        clan_rewarded = cached_state["clan_rewarded"]

        db_updates = {}
        if has_status != cached_state["has_status"]: db_updates["has_status"] = has_status
        if has_clan != cached_state["has_clan"]: db_updates["has_clan"] = has_clan

        guild = self.bot.get_guild(guild_id)
        if not guild: return
        member = guild.get_member(user_id)
        if not member: return

        target_role_id = status_role_id if tag_type == "status" else clan_role_id
        target_role = guild.get_role(int(target_role_id)) if target_role_id else None
        
        was_rewarded = status_rewarded if tag_type == "status" else clan_rewarded

        # KỊCH BẢN A: Khách thỏa mãn điều kiện -> Tặng Role luôn
        if is_valid and not was_rewarded:
            db_updates[f"{tag_type}_rewarded"] = True
            if target_role and target_role not in member.roles:
                try: await member.add_roles(target_role, reason=f"Hệ thống {tag_type.upper()} Tag")
                except Exception: pass
            
            task = asyncio.create_task(send_tag_message(self.bot, guild, member, tag_type))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        # KỊCH BẢN B: Khách mất điều kiện -> KIỂM DUYỆT CHÉO TRƯỚC KHI LỘT
        elif not is_valid and was_rewarded:
            db_updates[f"{tag_type}_rewarded"] = False
            
            cross_system = "clan" if tag_type == "status" else "status"
            cross_role_id = clan_role_id if tag_type == "status" else status_role_id
            cross_rewarded = clan_rewarded if tag_type == "status" else status_rewarded
            
            is_sharing_role = (str(target_role_id) == str(cross_role_id))
            
            if target_role and target_role in member.roles:
                if not (is_sharing_role and cross_rewarded):
                    try: await member.remove_roles(target_role, reason=f"Hệ thống {tag_type.upper()} Tag (Thu hồi)")
                    except Exception: pass

        if db_updates:
            await update_user_tag_state(self.bot, guild_id, user_id, db_updates)


    # ====================================================
    # MẮT THẦN 1: QUÉT TRẠNG THÁI (STATUS) 
    # ====================================================
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot: return
        config = await get_tag_config(self.bot, after.guild.id, "status")
        trigger = config.get("trigger")
        if not trigger: return
        
        has_status = False
        if after.activities:
            for act in after.activities:
                if getattr(act, "type", 0) == 4 or isinstance(act, discord.CustomActivity):
                    state = str(getattr(act, "state", getattr(act, "name", ""))).lower()
                    if trigger.lower() in state:
                        has_status = True
                        break
        
        await self.evaluate_member_tags(after.guild.id, after.id, "status", has_status)


    # ====================================================
    # MẮT THẦN 2: QUÉT CHỮ TRONG CLAN TAG (VÉT MÁNG TOÀN DIỆN)
    # ====================================================
    @commands.Cog.listener()
    async def on_socket_response(self, payload: dict):
        event_name = payload.get("t")
        if event_name not in ["MESSAGE_CREATE", "PRESENCE_UPDATE", "VOICE_STATE_UPDATE", "GUILD_MEMBER_UPDATE", "MESSAGE_REACTION_ADD"]:
            return
            
        data = payload.get("d", {})
        if not data: return
        
        guild_id = int(data.get("guild_id", 0))
        if not guild_id: return

        user_data = None
        if "member" in data and "user" in data["member"]:
            user_data = data["member"]["user"]
        elif "user" in data:
            user_data = data["user"]
        elif "author" in data:
            user_data = data["author"]
            
        if not user_data or user_data.get("bot"): return
        user_id = int(user_data.get("id", 0))
        if not user_id: return

        config = await get_tag_config(self.bot, guild_id, "clan")
        trigger = config.get("trigger")
        if not trigger: return

        # CHIẾN THUẬT LƯỚI QUÉT DÀY ĐẶC
        clan_tag_str = None
        member_data = data.get("member", {}) if isinstance(data.get("member"), dict) else {}
        
        # Discord thay đổi API liên tục, ta cào sạch các túi khả thi
        for tui in [data, user_data, member_data]:
            if isinstance(tui, dict):
                # Lục túi "clan"
                if "clan" in tui and isinstance(tui["clan"], dict):
                    if tui["clan"].get("tag"): clan_tag_str = tui["clan"].get("tag")
                # Lục túi "primary_guild"
                if "primary_guild" in tui and isinstance(tui["primary_guild"], dict):
                    if tui["primary_guild"].get("tag"): clan_tag_str = tui["primary_guild"].get("tag")
                
                # Tìm thấy rồi thì dừng lục lọi
                if clan_tag_str: break

        has_clan = False
        
        # So khớp chữ (Hỗ trợ 100% ký tự Unicode đặc biệt như ୨୧)
        if clan_tag_str and (trigger.lower() in str(clan_tag_str).lower()):
            has_clan = True

        await self.evaluate_member_tags(guild_id, user_id, "clan", has_clan)

async def setup(bot: commands.Bot):
    bot.tree.add_command(StatusTagGroup())
    bot.tree.add_command(ClanTagGroup())
    await bot.add_cog(ServerTagListener(bot))
    print("[load] success: core.servertag (Multi-IT, Tách đôi lệnh, Cross-Validation, Lưới Quét Toàn Diện)", flush=True)
