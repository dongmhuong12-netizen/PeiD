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
# LISTENER: HYBRID ARCHITECTURE (CHIA ĐỂ TRỊ)
# ======================

class ServerTagListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = set()

    def cog_unload(self):
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    # LÕI HỘI TỤ: Xử lý an toàn Database và Trao thưởng
    async def evaluate_and_reward(self, guild: discord.Guild, member: discord.Member, new_status: bool = None, new_clan: bool = None):
        config = await get_servertag_config(self.bot, guild.id)
        reward_role_id = config.get("reward_role_id")
        
        cached_state = await get_user_servertag_state(self.bot, guild.id, member.id)
        final_status = new_status if new_status is not None else cached_state["has_status"]
        final_clan = new_clan if new_clan is not None else cached_state["has_clan"]
        
        db_updates = {}
        if final_status != cached_state["has_status"]: db_updates["has_status"] = final_status
        if final_clan != cached_state["has_clan"]: db_updates["has_clan"] = final_clan

        is_eligible = (final_status or final_clan)
        was_rewarded = cached_state["is_rewarded"]

        # Chống dội lệnh dư thừa
        if not db_updates and is_eligible == was_rewarded:
            return

        if db_updates:
            await update_user_servertag_state(self.bot, guild.id, member.id, db_updates)

        reward_role = guild.get_role(int(reward_role_id)) if reward_role_id else None

        if is_eligible and not was_rewarded:
            await update_user_servertag_state(self.bot, guild.id, member.id, {"is_rewarded": True})
            if reward_role and reward_role not in member.roles:
                try: await member.add_roles(reward_role, reason="Servertag System")
                except Exception: pass
            
            task = asyncio.create_task(send_servertag_message(self.bot, guild, member))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        elif not is_eligible and was_rewarded:
            await update_user_servertag_state(self.bot, guild.id, member.id, {"is_rewarded": False})
            if reward_role and reward_role in member.roles:
                try: await member.remove_roles(reward_role, reason="Servertag System")
                except Exception: pass

    # ====================================================
    # LUỒNG 1: QUÉT TRẠNG THÁI (CHÍNH QUY - 100% HOẠT ĐỘNG)
    # ====================================================
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot: return
        config = await get_servertag_config(self.bot, after.guild.id)
        trigger = config.get("trigger_status")
        if not trigger: return
        
        has_status = False
        if after.activities:
            for act in after.activities:
                # Type 4 là định dạng Custom Status của API Discord
                if getattr(act, "type", 0) == 4 or isinstance(act, discord.CustomActivity):
                    state = str(getattr(act, "state", getattr(act, "name", ""))).lower()
                    if trigger.lower() in state:
                        has_status = True
                        break
        
        await self.evaluate_and_reward(after.guild, after, new_status=has_status)


    # ====================================================
    # LUỒNG 2: ĐÀO CLAN TAG (RAW GATEWAY PAYLOAD)
    # ====================================================
    @commands.Cog.listener()
    async def on_socket_response(self, payload: dict):
        if payload.get("t") != "GUILD_MEMBER_UPDATE":
            return
            
        data = payload.get("d", {})
        user_data = data.get("user", {})
        if user_data.get("bot"): return
        
        guild_id = int(data.get("guild_id", 0))
        user_id = int(user_data.get("id", 0))
        if not guild_id or not user_id: return

        # Đào sâu vào 2 vị trí khả thi nhất mà Discord cất giấu Clan Tag
        has_clan = False
        pg = user_data.get("primary_guild")
        clan = data.get("clan")
        
        if pg and isinstance(pg, dict):
            enabled = pg.get("identity_enabled", True)
            clan_id = pg.get("identity_guild_id") or pg.get("id")
            has_clan = (enabled and str(clan_id) == str(guild_id))
        elif clan and isinstance(clan, dict):
            has_clan = (str(clan.get("identity_guild_id")) == str(guild_id))

        guild = self.bot.get_guild(guild_id)
        if not guild: return
        
        member = guild.get_member(user_id)
        if not member:
            try: member = await guild.fetch_member(user_id)
            except discord.NotFound: return

        await self.evaluate_and_reward(guild, member, new_clan=has_clan)

async def setup(bot: commands.Bot):
    bot.tree.add_command(ServerTagGroup())
    await bot.add_cog(ServerTagListener(bot))
    print("[load] success: core.servertag (Hybrid Architecture - Phân tách Luồng an toàn)", flush=True)
