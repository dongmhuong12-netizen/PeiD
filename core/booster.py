import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks

# Import các công cụ quản lý bộ nhớ
from core.state import State
from core.cache_manager import get_raw, mark_dirty, save
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level, sync_all_boosters
from core.booster_storage import get_guild_config, save_guild_config
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

FILE_KEY = "booster_levels"

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
        config = await get_guild_config(interaction.guild.id)
        config["booster_role"] = role.id
        await save_guild_config(interaction.guild.id, config)
        
        # Sửa lỗi hiển thị: Title & Description chuẩn Mimu
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật role `booster` thành công",
            description=f"hiện tại **yiyi** sẽ sử dụng {role.mention} làm role quà tặng cho các booster nhé.",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # LOGIC PROACTIVE: tự động quét toàn server để gán role cho người đang boost
        asyncio.create_task(sync_all_boosters(interaction.guild))

    @app_commands.command(name="channel", description="đặt kênh thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """(2) cập nhật kênh thông báo"""
        config = await get_guild_config(interaction.guild.id)
        config["channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật kênh `boost` thành công: {channel.mention}",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):
        """(3) cập nhật nội dung tin nhắn"""
        config = await get_guild_config(interaction.guild.id)
        config["message"] = text
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật tin nhắn `boost` thành công: {text}",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed chúc mừng khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        """(4) & (5) gán embed mẫu"""
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"**yiyi** không tìm thấy embed có tên `{name}`. hãy kiểm tra lại bằng `/p embed edit` nhé",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        embed_success = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật embed `{name}` cho hệ thống `boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn chúc mừng boost và bảo vệ role 5p")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        """(6) & (7) giả lập gán role thông qua Engine và bảo vệ bypass"""
        await interaction.response.defer(ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        role_id = config.get("booster_role")
        role_obj = interaction.guild.get_role(role_id) if role_id else None
        role_mention = role_obj.mention if role_obj else "`none`"

        # [KIM BÀI MIỄN TỬ] Kích hoạt bảo vệ 5 phút trong State
        bypass_key = f"boost_test_{interaction.guild.id}_{interaction.user.id}"
        await State.set_ui(bypass_key, {"expiry": time.time() + 300})
        
        # Gán role ngay lập tức cho người test
        if role_obj:
            try:
                await interaction.user.add_roles(role_obj, reason="Virtual Boost Test (5m Bypass)")
            except:
                pass
        
        # Gửi thử tin nhắn chúc mừng
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        
        if success:
            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} test hệ thống `boost` thành công",
                description=f"**yiyi** đã gán role tạm thời cho {interaction.user.mention}. vai trò này sẽ được giữ trong **5 phút** để cậu kiểm tra trước khi vòng lặp định kỳ dọn dẹp.",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy đảm bảo rằng cậu đã setup đủ cấu hình cho `booster`, hoặc xem lại quyền của **yiyi** và quyền của kênh nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER & SYNC LOOP
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = set()
        # [QUY CHUẨN IT] Khởi động vòng lặp đồng bộ định kỳ 5 phút
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
            # IT Pro: Chạy cuốn chiếu từng server để tránh Rate Limit API
            await sync_all_boosters(guild)
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
            # Gán hoặc gỡ role dựa trên trạng thái boost thực tế
            task = asyncio.create_task(assign_correct_level(after))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            # Gửi tin nhắn chào mừng nếu là boost mới
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
    print("[load] success: core.booster (reconciliation loop & bypass active)", flush=True)
