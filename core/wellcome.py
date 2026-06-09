import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from collections import defaultdict # [VÁ LỖI]
import datetime # [CẤY GHÉP] Thư viện để tính giờ ca đêm

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.variable_engine import apply_variables
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# [VÁ LỖI] Lock theo Guild để bảo vệ trí nhớ cấu hình khi admin setup song song
_config_locks = defaultdict(asyncio.Lock)

# [CẤY GHÉP] Khóa chặt múi giờ Việt Nam (GMT+7)
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))

# ======================
# AUTOCOMPLETE HELPER (SAFE)
# ======================

async def _embed_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        from core.embed_storage import list_embeds
        embed_list = await list_embeds(interaction.guild_id)
        return [
            app_commands.Choice(name=name, value=name)
            for name in embed_list if current.lower() in name.lower()
        ][:25]
    except Exception:
        return []

# [CẤY GHÉP] Lấy danh sách văn bản từ kho AR cho lệnh night_shift
async def _ar_text_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        # Chọc thẳng vào db_texts của AR
        db_texts = getattr(interaction.client.db, "db", interaction.client.db)["ar_texts"]
        cursor = db_texts.find({"guild_id": interaction.guild_id})
        choices = []
        async for doc in cursor:
            name = doc.get("name")
            if name and current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
            if len(choices) >= 25: break
        return choices
    except Exception:
        return []

# ======================
# SEND MESSAGE HANDLER (ATOMIC)
# ======================

async def send_wellcome(guild: discord.Guild, member: discord.Member, bot_client: commands.Bot = None):
    """
    xử lý gửi tin nhắn wellcome phụ.
    gộp text và embed vào 1 request duy nhất để bảo vệ api discord.
    [NÂNG CẤP CA ĐÊM]: Tự động gửi kèm văn bản AR nếu đúng khung giờ thiết lập.
    """
    # [SỬA LỖI] Thêm await cho thao tác lấy data từ MongoDB
    config = await get_section(guild.id, "wellcome")
    if not config: return False

    # [GIA CỐ] Hỗ trợ đọc key mới và key cũ
    channel_id = config.get("channel_id") or config.get("channel")
    message_text = config.get("message")
    embed_name = config.get("embed_name") or config.get("embed")
    
    # [CẤY GHÉP] Đọc cấu hình ca đêm
    night_ar_text = config.get("night_ar_text")
    night_start = config.get("night_start")
    night_end = config.get("night_end")

    if not channel_id: return False

    channel = guild.get_channel(int(channel_id))
    if not channel: return False

    perms = channel.permissions_for(guild.me)
    if not perms.send_messages: return False

    try:
        final_content = ""
        final_embed = None

        # 1. xử lý text chính (Welcome ban ngày/24h)
        if message_text:
            final_content += apply_variables(message_text, guild, member)

        # 1.5 [CẤY GHÉP] Xử lý tham chiếu AR Ca Đêm (Time-Gated Reference)
        # Chỉ chạy nếu có thiết lập Night Shift VÀ có truyền bot_client vào
        if night_ar_text and night_start is not None and night_end is not None and bot_client:
            # Lấy giờ VN hiện tại
            now_vn = datetime.datetime.now(VN_TZ)
            current_hour = now_vn.hour
            
            is_night_time = False
            # Logic tính toán khung giờ xuyên đêm (vd: 22h đêm đến 6h sáng)
            if night_start < night_end:
                if night_start <= current_hour < night_end:
                    is_night_time = True
            else: # Ví dụ 22h -> 6h (night_start > night_end)
                if current_hour >= night_start or current_hour < night_end:
                    is_night_time = True
                    
            if is_night_time:
                # Sang kho AR lấy đồ
                db_texts = getattr(bot_client.db, "db", bot_client.db)["ar_texts"]
                ar_doc = await db_texts.find_one({"guild_id": guild.id, "name": night_ar_text})
                if ar_doc and ar_doc.get("content"):
                    parsed_night_text = apply_variables(ar_doc["content"], guild, member)
                    # Gộp text ban đêm vào text chính (xuống dòng cho đẹp)
                    if final_content:
                        final_content += f"\n\n{parsed_night_text}"
                    else:
                        final_content = parsed_night_text

        # Fix string rỗng của final_content
        if not final_content:
            final_content = None

        # 2. xử lý embed (đã thêm await cho load_embed)
        if embed_name and perms.embed_links:
            embed_data = await load_embed(guild.id, embed_name)
            if embed_data:
                from core.embed_sender import _build_embed
                processed_data = apply_variables(embed_data, guild, member)
                final_embed = _build_embed(processed_data)

        # 3. gửi gộp
        if final_content or final_embed:
            await channel.send(content=final_content, embed=final_embed)
            return True

        return False
    except Exception as e:
        print(f"[wellcome error] guild {guild.id} fail: {e}", flush=True)
        return False

# ======================
# WELLCOME GROUP (MEAT)
# ======================

# [DỌN RÁC KHÓA QUYỀN CỨNG] - Chuyển giao bảo mật cho Group /p tổng
class WellcomeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="wellcome", description="hệ thống chào mừng phụ")

    @app_commands.command(name="channel", description="đặt kênh gửi tin nhắn wellcome")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # [GIA CỐ] Defer chống treo
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # [SỬA LỖI] Thêm await và chuẩn hóa key thành channel_id
            await update_guild_config(gid, "wellcome", "channel_id", channel.id)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # [FIX] Dùng .name để tránh lộ mã ID thô trong Title
        # Văn phong mới: Chuyển sang Title Embed
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} đặt kênh `wellcome` thành công: {channel.name}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="message", description="đặt nội dung tin nhắn wellcome")
    async def message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # [SỬA LỖI] Thêm await
            await update_guild_config(gid, "wellcome", "message", message)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # [FIX] Dịch biến ngay lập tức để hiện mention tag trong phản hồi
        parsed_msg = apply_variables(message, interaction.guild, interaction.user)
        # Văn phong mới: Chuyển sang Title
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật tin nhắn `wellcome` thành công: {parsed_msg}",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="gán embed cho hệ thống wellcome")
    async def embed(self, interaction: discord.Interaction, name: str):
        # FIX: PHẢI AWAIT load_embed VÀ DEFER
        await interaction.response.defer(ephemeral=False)
        if not await load_embed(interaction.guild.id, name):
            # Văn phong mới: Title & Description
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} aree... có lỗi gì đó ở đây",
                description=f"hãy thử lại lần nữa nhé. **yiyi** không tìm thấy embed có tên `{name}`. xin hãy kiểm tra embed cậu muốn dùng cho wellcome bằng `/p embed edit`",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)
        
        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # [SỬA LỖI] Thêm await và chuẩn hóa key thành embed_name
            await update_guild_config(gid, "wellcome", "embed_name", name)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        # Văn phong mới: Chuyển sang Title
        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} cập nhật embed `{name}` cho hệ thống `wellcome` thành công",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    @embed.autocomplete('name')
    async def embed_autocomplete(self, interaction: discord.Interaction, current: str):
        return await _embed_name_autocomplete(interaction, current)

    # [CẤY GHÉP] Lệnh Setup Tham Chiếu AR Ca Đêm
    @app_commands.command(name="night_shift", description="cấu hình văn bản AR sẽ được chèn thêm vào welcome trong ca đêm")
    @app_commands.describe(
        ar_text_name="chọn tên văn bản từ kho AR để gửi bồi thêm",
        start_hour="giờ bắt đầu ca đêm (VD: 0 = 12h đêm, 22 = 10h tối)",
        end_hour="giờ kết thúc ca đêm (VD: 6 = 6h sáng)"
    )
    @app_commands.autocomplete(ar_text_name=_ar_text_autocomplete)
    async def night_shift(self, interaction: discord.Interaction, ar_text_name: str, start_hour: int, end_hour: int):
        await interaction.response.defer(ephemeral=False)
        
        # Rào chắn chống User ngáo nhập số linh tinh
        if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
            embed_err = discord.Embed(
                title=f"{Emojis.HOICHAM} giờ giấc không hợp lệ",
                description="cậu ơi, giờ chỉ được nằm trong khoảng từ `0` đến `23` thôi nhé.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)

        gid = interaction.guild.id
        lock = _config_locks[gid]
        async with lock:
            # Cập nhật song song 3 biến cấu hình
            await update_guild_config(gid, "wellcome", "night_ar_text", ar_text_name)
            await update_guild_config(gid, "wellcome", "night_start", start_hour)
            await update_guild_config(gid, "wellcome", "night_end", end_hour)
        if gid in _config_locks and not lock.locked(): _config_locks.pop(gid, None)
        
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} kích hoạt ca đêm thành công",
            description=f"từ `{start_hour}h` đến `{end_hour}h`, **yiyi** sẽ mượn văn bản `{ar_text_name}` để chào khách ca đêm nha.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="test", description="gửi thử tin nhắn wellcome")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        # Nạp bot_client vào hàm test để Yiyi móc nối kho AR (nếu đang là ca đêm)
        success = await send_wellcome(interaction.guild, interaction.user, bot_client=interaction.client)
        
        if success:
            # Văn phong mới: Title & Description
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} test `wellcome` thành công",
                description="hãy kiểm tra tại kênh được setup nhé. nếu không thấy embed, hãy kiểm tra lại quyền của **yiyi** hoặc quyền của kênh",
                color=0xe6e2dd
            )
        else:
            # Văn phong mới: Title & Description
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} hmm..? có vẻ có lỗi về cấu hình kênh hoặc embed",
                description="hãy kiểm tra lại khi đã đầy đủ `channel` `embed` `message` trước khi test nhé",
                color=0xe6e2dd
            )
        await interaction.followup.send(embed=embed)

# ======================
# LISTENER & INJECTION
# ======================

class WellcomeListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # [VÁ LỖI] Quản lý tác vụ để giải phóng bộ nhớ Member/Guild kịp thời
        self._tasks = set()

    def cog_unload(self):
        """[VÁ LỖI] Hủy toàn bộ tác vụ đang chờ khi reload module"""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # [VÁ LỖI + NÂNG CẤP CA ĐÊM] Truyền thêm self.bot vào để hàm send_wellcome lấy DB AR
        task = asyncio.create_task(send_wellcome(member.guild, member, bot_client=self.bot))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    # Khử bọc lệnh gốc, dùng chung giáp bảo vệ tổng của /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn nhánh cũ để chèn nhánh mới có night_shift
        existing_wellcome = next((c for c in p_cmd.commands if c.name == "wellcome"), None)
        if existing_wellcome:
            p_cmd.remove_command("wellcome")
            
        p_cmd.add_command(WellcomeGroup())
    else:
        print("[load] Warning: Master Group /p not found. Wellcome running independently.", flush=True)
    
    await bot.add_cog(WellcomeListener(bot))
    print("[load] success: core.wellcome (Industrial Sync & Night Shift Applied)", flush=True)
