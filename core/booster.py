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
        """(1) cập nhật role và kích hoạt truy quét chủ động"""
        config = await get_guild_config(interaction.guild.id)
        config["booster_role"] = role.id
        await save_guild_config(interaction.guild.id, config)
        
        # Văn phong (1)
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật role `booster` thành công: {role.mention}",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # LOGIC PROACTIVE: tự động quét toàn server để gán role cho người đang boost
        from core.booster_engine import sync_all_boosters
        asyncio.create_task(sync_all_boosters(interaction.guild))

    @app_commands.command(name="channel", description="đặt kênh thông báo khi có người boost")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """(2) cập nhật kênh thông báo"""
        config = await get_guild_config(interaction.guild.id)
        config["channel"] = channel.id
        await save_guild_config(interaction.guild.id, config)
        
        # Văn phong (2)
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
        
        # Văn phong (3)
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
            # Văn phong (4)
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"yiyi không tìm thấy embed có tên {name}. hãy kiểm tra lại bằng `/p embed edit` nhé",
                color=0xf8bbd0
            )
            return await interaction.response.send_message(embed=embed_err, ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        config["embed"] = name
        await save_guild_config(interaction.guild.id, config)
        
        # Văn phong (5)
        embed_success = discord.Embed(
            title=f"{Emojis.MATTRANG} cập nhật embed {name} cho hệ thống `boost` thành công",
            color=0xf8bbd0
        )
        await interaction.response.send_message(embed=embed_success, ephemeral=False)

    @app_commands.command(name="test", description="gửi thử tin nhắn chúc mừng boost và bảo vệ role 5p")
    @app_commands.default_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        """(6) & (7) giả lập gán role và bảo vệ bypass"""
        await interaction.response.defer(ephemeral=False)
        
        config = await get_guild_config(interaction.guild.id)
        role_id = config.get("booster_role")
        role_mention = "`none`"
        
        # LOGIC: Gán role vật lý cho người test
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    role_mention = role.mention
                except:
                    pass

        # [BYPASS LOGIC] Kích hoạt kim bài miễn tử 5 phút
        bypass_key = f"boost_test_{interaction.user.id}"
        await State.set_ui(bypass_key, {"expiry": time.time() + 300})
        
        success = await send_config_message(interaction.guild, interaction.user, "booster")
        
        if success:
            # Văn phong (6)
            embed = discord.Embed(
                title=f"{Emojis.MATTRANG} hệ thống `boost` được giả lập thành công",
                description=f"yiyi sẽ cho phép cậu giữ role {role_mention} trong 5 phút tới. sau 5 phút, yiyi sẽ gỡ role nếu cậu không có boost nhé {Emojis.YIYITIM}",
                color=0xf8bbd0
            )
        else:
            # Văn phong (7)
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description="hãy đảm bảo rằng cậu đã setup đủ cấu hình cho `booster`, hoặc xem lại quyền của yiyi và quyền của kênh nhé",
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
    print("[load] success: core.booster (logic fixed & persona applied)", flush=True)
