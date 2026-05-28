import discord
from discord import app_commands
from discord.ext import commands
import time
import io

from utils.emojis import Emojis
from core.embed_storage import load_embed, save_embed, get_all_embed_names

# =========================================================================
# AUTOCOMPLETE: Hỗ trợ tìm tên Embed
# =========================================================================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        choices = [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]
        return choices
    except Exception:
        return []

# =========================================================================
# GIAO DIỆN FORM (MODALS) - HỆ THỐNG ẨN DANH
# =========================================================================

class AnonCreateModal(discord.ui.Modal, title="tạo bài đăng ẩn danh"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
        self.post_title = discord.ui.TextInput(
            label="tiêu đề bài viết (tùy chọn)",
            placeholder="nhập tiêu đề bài viết...",
            required=False,
            max_length=256,
            style=discord.TextStyle.short
        )
        self.post_content = discord.ui.TextInput(
            label="nội dung",
            placeholder="nhập nội dung cậu muốn gửi gắm...",
            required=True,
            max_length=4000,
            style=discord.TextStyle.paragraph
        )
        self.post_image = discord.ui.TextInput(
            label="link ảnh/video (tùy chọn)",
            placeholder="dán link ảnh cdn từ cỗ máy /p image vào đây...",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.post_title)
        self.add_item(self.post_content)
        self.add_item(self.post_image)

    async def on_submit(self, interaction: discord.Interaction):
        db_config = getattr(self.bot.db, "db", self.bot.db)["anon_config_sys"]
        db_users = getattr(self.bot.db, "db", self.bot.db)["anon_users_sys"]
        db_posts = getattr(self.bot.db, "db", self.bot.db)["anon_posts_sys"]

        await interaction.response.defer(ephemeral=True)

        # 1. Kiểm tra cấu hình hệ thống
        config = await db_config.find_one({"guild_id": str(interaction.guild_id)})
        if not config or not config.get("post_channel") or not config.get("log_channel"):
            return await interaction.followup.send(f"{Emojis.HOICHAM} hệ thống chưa đủ cấu hình. hãy thử lại khi đã setup đầy đủ nhé.", ephemeral=True)

        post_channel = interaction.guild.get_channel(int(config["post_channel"]))
        log_channel = interaction.guild.get_channel(int(config["log_channel"]))
        
        if not post_channel or not log_channel:
            return await interaction.followup.send(f"{Emojis.HOICHAM} hệ thống chưa đủ cấu hình. hãy thử lại khi đã setup đầy đủ nhé.", ephemeral=True)

        # 2. Xử lý bộ đếm User STT
        user_id = str(interaction.user.id)
        user_data = await db_users.find_one_and_update(
            {"user_id": user_id, "guild_id": str(interaction.guild_id)},
            {"$inc": {"total_posts": 1}},
            upsert=True,
            return_document=True
        )
        stt = user_data["total_posts"]

        # 3. Đúc Embed công khai và nã đạn
        title_val = self.post_title.value.strip() or "Bài viết ẩn danh"
        content_val = self.post_content.value.strip()
        image_val = self.post_image.value.strip()
        
        embed_post = discord.Embed(
            title=title_val,
            description=content_val,
            color=0xe6e2dd,
            timestamp=discord.utils.utcnow()
        )
        embed_post.set_footer(text=f"Bài viết ẩn danh #{stt}")

        if image_val:
            embed_post.set_image(url=image_val)

        try:
            msg = await post_channel.send(embed=embed_post)
        except Exception as e:
            return await interaction.followup.send(f"{Emojis.HOICHAM} nghẽn mạch khi gửi bài đăng: `{e}`", ephemeral=True)

        # 4. Lưu Bộ nhớ 10 phút (TTL Logic)
        await db_posts.insert_one({
            "guild_id": str(interaction.guild_id),
            "user_id": user_id,
            "stt": stt,
            "message_id": str(msg.id),
            "title": title_val,
            "content": content_val,
            "image": image_val,
            "timestamp": int(time.time())
        })

        # 5. Đóng gói file Log và gửi đi
        txt_content = f"Tiêu đề: {title_val}\n\nNội dung:\n{content_val}"
        if image_val:
            txt_content += f"\n\nLink đính kèm: {image_val}"
        file_obj = discord.File(io.BytesIO(txt_content.encode("utf-8")), filename=f"post_{stt}.txt")
        log_msg = f"[TẠO MỚI] tác giả: {interaction.user.mention} (`{interaction.user.id}`) | stt bài viết: #{stt} | tổng số bài đã đăng: {stt}"
        
        try:
            await log_channel.send(content=log_msg, file=file_obj)
        except:
            pass # Bỏ qua nếu mất log để không làm gián đoạn UX

        # 6. Báo cáo thành công
        await interaction.followup.send(f"{Emojis.BUOMA} đăng bài thành công. số thứ tự bài viết: #{stt}", ephemeral=True)


class AnonEditFormModal(discord.ui.Modal, title="chỉnh sửa bài đăng"):
    def __init__(self, bot, post_data):
        super().__init__()
        self.bot = bot
        self.post_data = post_data
        
        self.post_title = discord.ui.TextInput(
            label="tiêu đề bài viết (tùy chọn)",
            default=post_data.get("title", ""),
            required=False,
            max_length=256,
            style=discord.TextStyle.short
        )
        self.post_content = discord.ui.TextInput(
            label="nội dung",
            default=post_data.get("content", ""),
            required=True,
            max_length=4000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.post_title)
        self.add_item(self.post_content)

    async def on_submit(self, interaction: discord.Interaction):
        db_config = getattr(self.bot.db, "db", self.bot.db)["anon_config_sys"]
        db_posts = getattr(self.bot.db, "db", self.bot.db)["anon_posts_sys"]

        await interaction.response.defer(ephemeral=True)

        config = await db_config.find_one({"guild_id": str(interaction.guild_id)})
        post_channel = interaction.guild.get_channel(int(config["post_channel"]))
        log_channel = interaction.guild.get_channel(int(config["log_channel"]))

        title_val = self.post_title.value.strip() or "Bài viết ẩn danh"
        content_val = self.post_content.value.strip()
        stt = self.post_data["stt"]

        # 1. Cập nhật Embed công khai
        try:
            msg = await post_channel.fetch_message(int(self.post_data["message_id"]))
            embed_post = msg.embeds[0]
            embed_post.title = title_val
            embed_post.description = content_val
            await msg.edit(embed=embed_post)
        except discord.NotFound:
            # DEF: Nếu tin nhắn bay màu, xóa luôn DB để giữ sạch
            await db_posts.delete_one({"_id": self.post_data["_id"]})
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy bài viết trên kênh, có thể đã bị quản trị viên xóa.", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"{Emojis.HOICHAM} lỗi truyền tải mạch cập nhật: `{e}`", ephemeral=True)

        # 2. Cập nhật DB
        await db_posts.update_one(
            {"_id": self.post_data["_id"]},
            {"$set": {"title": title_val, "content": content_val}}
        )

        # 3. Ném Log mới
        txt_content = f"Tiêu đề: {title_val}\n\nNội dung:\n{content_val}"
        file_obj = discord.File(io.BytesIO(txt_content.encode("utf-8")), filename=f"post_{stt}_edited.txt")
        log_msg = f"[CẬP NHẬT] tác giả: {interaction.user.mention} (`{interaction.user.id}`) | stt bài viết: #{stt}"
        try:
            await log_channel.send(content=log_msg, file=file_obj)
        except:
            pass

        await interaction.followup.send(f"{Emojis.BUOMA} cập nhật nội dung bài viết #{stt} thành công.", ephemeral=True)


class AnonEditFindModal(discord.ui.Modal, title="tìm bài đăng để sửa"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.stt_input = discord.ui.TextInput(
            label="nhập stt bài viết của cậu (vd: 1, 2)",
            placeholder="chỉ nhập con số...",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.stt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stt_target = int(self.stt_input.value.strip())
        except ValueError:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} mã số thứ tự không hợp lệ. xin hãy nhập lại.", ephemeral=True)

        db_posts = getattr(self.bot.db, "db", self.bot.db)["anon_posts_sys"]
        
        # Truy xuất và kiểm toán 10 phút
        post_data = await db_posts.find_one({"guild_id": str(interaction.guild_id), "user_id": str(interaction.user.id), "stt": stt_target})
        
        if not post_data:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} không tìm thấy bài viết hoặc đã quá hạn. cậu chỉ có thể chỉnh sửa hoặc xoá bài trong 10 phút.", ephemeral=True)

        # ATK: Quét thời gian thực, nếu quá 600s -> Băm nát dữ liệu giải phóng RAM/DB ngay lập tức
        if time.time() - post_data["timestamp"] > 600:
            await db_posts.delete_one({"_id": post_data["_id"]})
            return await interaction.response.send_message(f"{Emojis.HOICHAM} không tìm thấy bài viết hoặc đã quá hạn. cậu chỉ có thể chỉnh sửa hoặc xoá bài trong 10 phút.", ephemeral=True)

        # Trạm trung chuyển để lách luật UI Discord (Không cho xếp chồng Modal)
        view = discord.ui.View(timeout=120)
        btn = discord.ui.Button(label=f"mở form sửa bài #{stt_target}", style=discord.ButtonStyle.secondary, emoji=Emojis.BUOMB)
        
        async def btn_callback(i: discord.Interaction):
            await i.response.send_modal(AnonEditFormModal(self.bot, post_data))
            
        btn.callback = btn_callback
        view.add_item(btn)
        
        await interaction.response.send_message(f"{Emojis.BUOMA} đã tìm thấy bài viết #{stt_target}. cậu hãy nhấn nút bên dưới để mở giao diện chỉnh sửa nhe.", view=view, ephemeral=True)


class AnonDeleteModal(discord.ui.Modal, title="xóa bài đăng vĩnh viễn"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.stt_input = discord.ui.TextInput(
            label="nhập stt bài viết của cậu (vd: 1, 2)",
            placeholder="chỉ nhập con số...",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.stt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stt_target = int(self.stt_input.value.strip())
        except ValueError:
            return await interaction.response.send_message(f"{Emojis.HOICHAM} mã số thứ tự không hợp lệ. xin hãy nhập lại.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        db_config = getattr(self.bot.db, "db", self.bot.db)["anon_config_sys"]
        db_posts = getattr(self.bot.db, "db", self.bot.db)["anon_posts_sys"]

        post_data = await db_posts.find_one({"guild_id": str(interaction.guild_id), "user_id": str(interaction.user.id), "stt": stt_target})
        
        if not post_data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy bài viết hoặc đã quá hạn. cậu chỉ có thể chỉnh sửa hoặc xoá bài trong 10 phút.", ephemeral=True)

        # ATK: Quét giới hạn 10 phút
        if time.time() - post_data["timestamp"] > 600:
            await db_posts.delete_one({"_id": post_data["_id"]})
            return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy bài viết hoặc đã quá hạn. cậu chỉ có thể chỉnh sửa hoặc xoá bài trong 10 phút.", ephemeral=True)

        config = await db_config.find_one({"guild_id": str(interaction.guild_id)})
        post_channel = interaction.guild.get_channel(int(config["post_channel"]))
        log_channel = interaction.guild.get_channel(int(config["log_channel"]))

        # 1. Trục xuất tin nhắn vật lý
        try:
            msg = await post_channel.fetch_message(int(post_data["message_id"]))
            await msg.delete()
        except discord.NotFound:
            pass # Tin nhắn không tồn tại thì bỏ qua, cứ xóa DB

        # 2. Xóa sổ Database
        await db_posts.delete_one({"_id": post_data["_id"]})

        # 3. Ghi Log xóa
        log_msg = f"[XÓA BÀI] tác giả: {interaction.user.mention} (`{interaction.user.id}`) | stt bài viết: #{stt_target} (đã hủy thực thể trên kênh)"
        try:
            await log_channel.send(content=log_msg)
        except:
            pass

        await interaction.followup.send(f"{Emojis.BUOMA} xoá bài viết #{stt_target} thành công.", ephemeral=True)


# =========================================================================
# PHÂN HỆ LỆNH & LẮNG NGHE SỰ KIỆN NÚT BẤM
# =========================================================================

class AnonSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_premium = getattr(bot.db, "db", bot.db)["premium_users_sys"]
        self.db_config = getattr(bot.db, "db", bot.db)["anon_config_sys"]

    async def has_premium_privilege(self, user_id: int) -> bool:
        if user_id == self.bot.boss_id:
            return True
        record = await self.db_premium.find_one({"user_id": str(user_id)})
        return record is not None

    def get_unauthorized_embed(self) -> discord.Embed:
        return discord.Embed(
            title=f"{Emojis.BUOMA} không được rồi, xin lỗi cậu nhe..",
            description="lệnh đặc cách này chỉ có người sáng lập mới có thể sử dụng.",
            color=0xe6e2dd
        )

    # -------------------------------------------------------------------------
    # LISTENER: Bắt sóng nút bấm toàn hệ thống
    # -------------------------------------------------------------------------
    @commands.Cog.listener("on_interaction")
    async def on_button_click(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "anon_btn_create":
            await interaction.response.send_modal(AnonCreateModal(self.bot))
        elif custom_id == "anon_btn_edit":
            await interaction.response.send_modal(AnonEditFindModal(self.bot))
        elif custom_id == "anon_btn_delete":
            await interaction.response.send_modal(AnonDeleteModal(self.bot))

    # -------------------------------------------------------------------------
    # LỆNH SETUP (DÀNH CHO SẾP)
    # -------------------------------------------------------------------------
    anon_setup = app_commands.Group(name="anon_setup", description="[PREMIUM] Cấu hình hệ thống bài viết ẩn danh")

    @anon_setup.command(name="post_channel", description="[PREMIUM] gán kênh sẽ xuất hiện các bài viết ẩn danh")
    @app_commands.describe(channel="chọn kênh đăng bài công khai")
    async def setup_post_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.has_premium_privilege(interaction.user.id):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await self.db_config.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {"post_channel": str(channel.id)}},
            upsert=True
        )
        await interaction.followup.send(f"{Emojis.BUOMA} liên kết thành công. các bài đăng ẩn danh sẽ được gửi tới {channel.mention}.", ephemeral=True)

    @anon_setup.command(name="log_channel", description="[PREMIUM] gán kênh lưu trữ nhật ký và dữ liệu bài đăng")
    @app_commands.describe(channel="chọn kênh bí mật để lưu log")
    async def setup_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.has_premium_privilege(interaction.user.id):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await self.db_config.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {"log_channel": str(channel.id)}},
            upsert=True
        )
        await interaction.followup.send(f"{Emojis.BUOMA} liên kết thành công. nhật ký kiểm toán sẽ được gửi tới {channel.mention}.", ephemeral=True)

    @anon_setup.command(name="link", description="[PREMIUM] gắn nút bấm ẩn danh vào embed đã thiết kế")
    @app_commands.describe(name="chọn embed muốn gắn bảng điều khiển")
    @app_commands.autocomplete(name=embed_name_autocomplete)
    async def setup_link(self, interaction: discord.Interaction, name: str):
        if not await self.has_premium_privilege(interaction.user.id):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        embed_name_clean = name.strip().lower()

        data = await load_embed(interaction.guild.id, embed_name_clean)
        if not data:
            return await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không tìm thấy embed có tên `{embed_name_clean}`, xin hãy kiểm tra lại nhé", ephemeral=True)

        # Ghi đè mảng nút bấm ẩn danh chuẩn logic
        data["buttons"] = [
            {"label": "create", "emoji": "{TYM}", "style": "secondary", "type": "button", "custom_id": "anon_btn_create"},
            {"label": "edit", "emoji": "{BUOMB}", "style": "secondary", "type": "button", "custom_id": "anon_btn_edit"},
            {"label": "delete", "emoji": "{MOONBL}", "style": "secondary", "type": "button", "custom_id": "anon_btn_delete"}
        ]
        
        await save_embed(interaction.guild.id, embed_name_clean, data)
        await interaction.followup.send(f"{Emojis.BUOMA} liên kết thành công. bảng điều khiển đã được gắn vào hệ thống.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AnonSystem(bot))
    print("[LOAD] Success: commands.systems.anon_system (Anonymous Engine Loaded)", flush=True)
