import asyncio
import discord
import time
from discord import app_commands
from discord.ext import commands

# Import các công cụ quản lý bộ nhớ
from core.state import State
from core.cache_manager import get_raw, mark_dirty, save
from core.embed_storage import load_embed
from core.greet_leave import send_config_message
from core.booster_engine import assign_correct_level
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
        config = await get_guild_config(interaction.guild.id)
        config["booster_role"] = role.id
        await save_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"đặt `booster role` thành công: {role.mention}", ephemeral=False)

    @app_commands.command(name="channel", description="đặt kênh thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = await get_guild_config(interaction.guild.id)
        config["channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        await interaction.response.send_message(f"đặt kênh `boost` thành công: {channel.mention}", ephemeral=False)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):
        config = await get_guild_config(interaction.guild.id)
        config["message"] = text
        await save_guild_config(interaction.guild.id, config)
        
        embed = discord.Embed(
            description=f"{Emojis.MATTRANG} cập nhật nội dung `boost` thành công: `{text}`",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="embed", description="gán embed chúc mừng khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):
        if not await load_embed(interaction.guild.id, name):
            embed_err = discord.Embed(
                description=f"{Emojis.HOICHAM} aree... yiyi không tìm thấy embed có tên `{name}`. hãy kiểm tra lại bằng `/p embed edit` nhé",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        embed_success = discord.Embed(
            description=f"{Emojis.MATTRANG} gán embed `{name}` cho hệ thống `boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn chúc mừng boost và bảo vệ role 5p")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        """kích hoạt chế độ test: giả lập gán role và cấp kim bài miễn tử 5 phút."""
        await interaction.response.defer(ephemeral=False)
        
        # 1. KIỂM TRA VÀ GÁN ROLE THẬT ĐỂ TEST /P BOOSTER ROLE
        config = await get_guild_config(interaction.guild.id)
        role_id = config.get("booster_role")
        role_status = "không tìm thấy role"
        
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    role_status = role.mention
                except:
                    role_status = "thiếu quyền gán role"

        # 2. [BYPASS LOGIC] Ghi đè thời gian bảo vệ vào RAM (300s = 5 phút)
        bypass_key = f"boost_test_{interaction.user.id}"
        await State.set_ui(bypass_key, {"expiry": time.time() + 300})
        
        # 3. GỬI EMBED CHÚC MỪNG
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        
        if success:
            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} hệ thống `boost` đã được giả lập thành công",
                description=f"yiyi sẽ cho phép cậu giữ role booster trong 5 phút tới. sau 5 phút, yiyi sẽ gỡ role nếu cậu không có boost nhé {Emojis.YIYITIM}\n\n{Emojis.MATTRANG} booster role: {role_status}",
                color=0xf8bbd0
            )
        else:
            embed = discord.Embed(
                description=f"{Emojis.HOICHAM} kiểm tra thất bại, hãy xem lại cấu hình kênh hoặc embed nhé",
                color=0xf8bbd0
            )
        await interaction.followup.send(embed=embed, ephemeral=False)

# ======================
# LISTENER (CHỐT CHẶN THỜI GIAN THỰC)
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [XOÁ BỎ] Radar quét ngầm 5 phút đã bị loại bỏ để tối ưu tài nguyên
        self._tasks = set()

    def cog_unload(self):
        """dọn dẹp các tác vụ ngầm khi reload module"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """chỉ xử lý khi có biến động trạng thái boost thực tế hoặc hết hạn test"""
        if after.bot: return
        
        # [CHỐT CHẶN BYPASS] Kiểm tra xem thành viên có đang trong 5 phút test không
        bypass_key = f"boost_test_{after.id}"
        state_data = await State.get_ui(bypass_key)
        if state_data and time.time() < state_data.get("expiry", 0):
            return # Đang trong thời gian bảo vệ, không gỡ role

        # [LOGIC ĐA ĐIỀM] Kiểm tra thay đổi boost hoặc thay đổi role sau khi hết hạn test
        boost_changed = before.premium_since != after.premium_since
        role_changed = before.roles != after.roles
        
        if boost_changed or role_changed:
            # gửi tin nhắn chào mừng nếu là boost mới
            if before.premium_since is None and after.premium_since is not None:
                task_welcome = asyncio.create_task(send_config_message(after.guild, after, "booster"))
                self._tasks.add(task_welcome)
                task_welcome.add_done_callback(self._tasks.discard)
            
            # gọi engine để gán hoặc gỡ role booster gốc
            task_sync = asyncio.create_task(assign_correct_level(after))
            self._tasks.add(task_sync)
            task_sync.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        if not any(c.name == "boost" for c in p_cmd.commands):
            p_cmd.add_command(BoostGroup())
    await bot.add_cog(BoosterListener(bot))
    print("[load] success: core.booster (check boost logic fixed)", flush=True)
