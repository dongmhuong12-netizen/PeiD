import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Import các công cụ quản lý bộ nhớ
from core.state import State
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level, sync_all_boosters
from core.booster_storage import get_guild_config, save_guild_config
from core.variable_engine import apply_variables 
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# ======================
# BOOST GROUP (CHỈ GIỮ BOOSTER THƯỜNG)
# ======================

class BoostGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="boost", description="hệ thống quản lý server boost")

    @app_commands.command(name="role", description="đặt booster role định danh của server")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role):
        """(1) cập nhật role và kích hoạt truy quét chủ động"""
        # [GIA CỐ] Defer ngay lập tức để tránh lỗi Unknown Interaction
        await interaction.response.defer(ephemeral=False)
        
        print(f"[BOOST] Đang setup role {role.name} cho server {interaction.guild.id}", flush=True)
        
        # [GIA CỐ] DAL an toàn
        config = await get_guild_config(interaction.guild.id)
        config["booster_role"] = role.id
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật role `booster` thành công: {role.name}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

        # LOGIC PROACTIVE: tự động quét toàn server để gán role cho người đang boost
        asyncio.create_task(sync_all_boosters(interaction.guild))

    @app_commands.command(name="channel", description="đặt kênh thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """(2) cập nhật kênh thông báo"""
        await interaction.response.defer(ephemeral=False)
        
        print(f"[BOOST] Đang setup channel {channel.name} cho server {interaction.guild.id}", flush=True)
        config = await get_guild_config(interaction.guild.id)
        # [SỬA LỖI BIẾN]: Cập nhật cả key mới để Dashboard luôn hiện data chính xác
        config["channel_id"] = channel.id
        config["channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật kênh `boost` thành công: {channel.name}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):
        """(3) cập nhật nội dung tin nhắn"""
        await interaction.response.defer(ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["message"] = text
        await save_guild_config(interaction.guild.id, config)
        
        display_text = apply_variables(text, interaction.guild, interaction.user)
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật tin nhắn `boost` thành công: {display_text}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="gán embed chúc mừng khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        """(4) & (5) gán embed mẫu"""
        await interaction.response.defer(ephemeral=False)
        
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`. hãy kiểm tra lại bằng `/p embed edit` nhé",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)
        
        config = await get_guild_config(interaction.guild.id)
        # [SỬA LỖI BIẾN]: Chuẩn hóa key embed_name cho Dashboard
        config["embed_name"] = name
        config["embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật embed `{name}` cho hệ thống `boost` thành công",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @app_commands.command(name="test", description="gửi thử tin nhắn chúc mừng boost và bảo vệ role 5p")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        """(6) & (7) giả lập gán role thông qua Engine và bảo vệ bypass"""
        print(f"[DEBUG] Đang chạy lệnh test boost cho {interaction.user.name}...", flush=True)
        await interaction.response.defer(ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        role_id = config.get("booster_role")
        role_obj = interaction.guild.get_role(int(role_id)) if role_id else None
        rolesetup = role_obj.mention if role_obj else "`none`"

        # [KIM BÀI MIỄN TỬ] Kích hoạt bảo vệ 5 phút trong State
        # Đồng bộ Key tuyệt đối với Booster Engine
        bypass_key = f"boost_test_{interaction.guild.id}_{interaction.user.id}"
        await State.set_ui(bypass_key, {"expiry": time.time() + 300})
        
        if role_obj:
            try:
                await interaction.user.add_roles(role_obj, reason="Virtual Boost Test (5m Bypass)")
            except:
                pass
        
        # [GIA CỐ] Gọi send_config_message đảm bảo đồng bộ biến
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        
        if success:
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} test hệ thống `boost` thành công",
                description=f"yiyi sẽ cho phép cậu giữ role {rolesetup} trong 5 phút tới để kiểm tra cấu hình. sau 5 phút, yiyi sẽ gỡ role nếu cậu không có boost nhé",
                color=0xe6e2dd
            )
        else:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy đảm bảo rằng cậu đã setup đủ cấu hình cho `booster`, hoặc xem lại quyền của **yiyi** và quyền của kênh nhé",
                color=0xe6e2dd
            )
        await interaction.followup.send(embed=embed)

# ======================
# LISTENER & SYNC LOOP
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = set()
        self.reconciliation_loop.start()

    def cog_unload(self):
        self.reconciliation_loop.cancel()
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @tasks.loop(minutes=5)
    async def reconciliation_loop(self):
        """Vòng lặp đồng bộ: gán cho boost, gỡ cho không boost (Bypass 5p)"""
        for guild in self.bot.guilds:
            try:
                # [INDUSTRIAL] Gọi sync_all_boosters để quét sạch member no-boost/test-expired
                await sync_all_boosters(guild)
            except:
                continue
            await asyncio.sleep(0.5) 

    @reconciliation_loop.before_loop
    async def before_reconciliation(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Xử lý biến động boost thời gian thực"""
        if after.bot: return
        
        boost_changed = before.premium_since != after.premium_since
        if boost_changed:
            # Gán role/Level mới thông qua Engine
            task = asyncio.create_task(assign_correct_level(after))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            # Gửi tin nhắn mừng nếu bắt đầu boost
            if before.premium_since is None and after.premium_since is not None:
                task_welcome = asyncio.create_task(send_config_message(after.guild, after, "booster"))
                self._tasks.add(task_welcome)
                task_welcome.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "boost" for c in p_cmd.commands):
            p_cmd.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
    print("[load] success: core.booster (Standardized & Expire Fix)", flush=True)
