import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import copy

from core.embed_ui import EmbedUIView, ACTIVE_EMBED_VIEWS
from core.embed_storage import load_embed, delete_embed, get_all_embed_names
from core.embed_sender import send_embed, _build_embed
from systems.embed_system import EmbedSystem
from core.variable_engine import apply_variables

# IMPORT ENGINE IMAGE MỚI (Xử lý CDN vĩnh viễn)
from core.image_engine import process_image_upload
# IMPORT EMOJI HỆ THỐNG
from utils.emojis import Emojis

# =============================
# HELPERS (Bổ trợ) - GIỮ NGUYÊN 100% DNA CỦA NGUYỆT
# =============================

async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    [VÁ LỖI CHÍ MẠNG - NÂNG CẤP INDUSTRIAL] 
    Autocomplete thần tốc hỗ trợ cả chuỗi đơn và chuỗi nhiều tên (cách nhau bởi dấu phẩy).
    """
    guild = interaction.guild
    if not guild: return []
    
    try:
        # [KẾT NỐI MẠCH] Phải await vì storage giờ đã lên Cloud Atlas
        names = await get_all_embed_names(guild.id)
        
        # MẠCH XỬ LÝ CHUỖI ĐA TẦNG: Hỗ trợ gợi ý sau dấu phẩy
        if "," in current:
            parts = current.split(",")
            to_complete = parts[-1].strip().lower()
            prefix = ",".join(parts[:-1]) + ", "
        else:
            to_complete = current.strip().lower()
            prefix = ""

        choices = [
            app_commands.Choice(name=f"{prefix}{name}", value=f"{prefix}{name}") 
            for name in names if to_complete in name.lower()
        ][:25]
        
        return choices
    except Exception:
        # IT Pro: Tránh lỗi 404 Unknown Interaction
        return []

def _cleanup_views(key: str):
    views = ACTIVE_EMBED_VIEWS.get(key)
    if not views: return
    for view in list(views):
        if hasattr(view, "message") and view.message:
            try: asyncio.create_task(view.message.delete())
            except: pass
        view.stop()
    ACTIVE_EMBED_VIEWS[key] = []

# [BỔ SUNG PHASE 3] Hàm tạo View nút bấm từ dữ liệu lưu trữ
def create_embed_view(data):
    buttons_data = data.get("buttons", [])
    if not buttons_data: return None
    
    # [INDUSTRIAL] timeout=None để nút luôn sống vĩnh viễn trên kênh được show
    view = discord.ui.View(timeout=None)
    
    # Map màu sắc nút chuẩn Industrial
    style_map = {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
    }

    for btn in buttons_data:
        b_type = btn.get("type")
        
        # 1. MẠCH NÚT LINK (Chuyển hướng)
        if b_type == "link":
            view.add_item(discord.ui.Button(
                label=btn.get("label"), 
                url=btn.get("url"), 
                emoji=btn.get("emoji")
            ))
            
        # 2. MẠCH NÚT HỆ THỐNG (Multi-IT: Chấp nhận mọi loại Button tương tác)
        elif b_type == "button":
            # Tự động nhận diện Style, Label và CustomID để kích hoạt hệ thống tương ứng
            view.add_item(discord.ui.Button(
                style=style_map.get(btn.get("style", "secondary").lower(), discord.ButtonStyle.secondary),
                label=btn.get("label"),
                custom_id=btn.get("custom_id"),
                emoji=btn.get("emoji")
            ))
            
    return view

# =============================
# IMAGE COMMAND (BỔ SUNG VÀO HỆ LỆNH /P)
# =============================

@app_commands.command(name="image", description="upload file to get permanent cdn link")
@app_commands.describe(file="select the image, gif or video file to get link")
async def p_image_cmd(interaction: discord.Interaction, file: discord.Attachment):
    """Lệnh /p image xử lý upload và tạo link CDN vĩnh viễn"""
    # Tư duy IT Pro: Defer ngay lập tức để tránh lỗi Interaction Failed khi xử lý file lớn
    await interaction.response.defer(ephemeral=False)
    # Gọi logic xử lý từ core engine (Chuyển tiếp interaction và client)
    await process_image_upload(interaction, file, interaction.client)

# =============================
# EMBED MODULE LOGIC (KHÔI PHỤC TOÀN BỘ CẤU TRÚC LỆNH)
# =============================

class EmbedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="embed", description="hệ thống quản lý embed chuyên sâu")

    @app_commands.command(name="create", description="tạo embed thiết kế mới")
    @app_commands.describe(name="nhập tên embed mới muốn tạo")
    async def create(self, interaction: discord.Interaction, name: str):
        # QUY TẮC 3S: Defer ngay lập tức để giữ mạch kết nối với Discord (Industrial Standard)
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        
        # [KẾT NỐI MẠCH] Load từ Cloud phải dùng await
        if await load_embed(guild.id, name):
            embed_exists = discord.Embed(
                title=f"{Emojis.MATTRANG} embed tên `{name}` đã tồn tại",
                description=f"nếu cậu không tìm thấy embed, hãy thử dùng `/p embed edit` để tìm lại nhé",
                color=0xf8bbd0
            )
            return await interaction.followup.send(embed=embed_exists)

        key = f"{guild.id}:{name}"
        _cleanup_views(key)

        # [KẾT NỐI MẠCH] Logic tạo bản ghi ban đầu trên Cloud
        success, error = await EmbedSystem.create_embed(guild.id, name)
        
        if not success:
            return await interaction.followup.send(f"phát sinh lỗi khi tạo embed `{error}`")

        # Nạp dữ liệu vừa tạo từ Cloud
        embed_data = await load_embed(guild.id, name)
        
        # [VÁ LỖI] Khởi tạo View (View sẽ tự đăng ký vào ACTIVE_EMBED_VIEWS để quản lý RAM)
        view = EmbedUIView(guild.id, name, embed_data, timeout=600.0)
        embed = view.build_embed()

        msg = await interaction.followup.send(
            content=(
                f"• đã tạo embed với tên `{name}`\n"
                "• sử dụng các nút bên dưới để chỉnh sửa embed\n"
                f"• cậu có thể sử dụng embed này để tạo tin nhắn tiếp tân (greet/leave - wellcome), tạo embed chúc mừng cho booster, các banner hệ thống khi dùng lệnh `/p embed show` hoặc setup pick role"
            ),
            embed=embed,
            view=view
        )
        
        view.message = msg

    @app_commands.command(name="edit", description="chỉnh sửa embed hiện có")
    @app_commands.describe(
        name="chọn embed muốn chỉnh sửa từ danh sách",
        extra_embeds="nhập tên các embed khác, cách nhau bằng dấu phẩy (vd: b, c)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete, extra_embeds=embed_name_autocomplete)
    async def edit(self, interaction: discord.Interaction, name: str, extra_embeds: str = None):
        # IT Standard Defer: Tránh lỗi "Interaction Failed" khi Cloud phản hồi chậm
        await interaction.response.defer(ephemeral=False)
        
        # Gom danh sách
        embed_names = [name]
        if extra_embeds:
            embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])

        # Vòng lặp xả bảng UI chỉnh sửa hàng loạt
        for emb_name in embed_names:
            # [KẾT NỐI MẠCH] Await để nạp linh hồn embed từ MongoDB
            data = await load_embed(interaction.guild.id, emb_name)
            if not data:
                embed_none = discord.Embed(
                    title=f"{Emojis.HOICHAM} hmm...?",
                    description=f"**yiyi** không tìm thấy embed có tên `{emb_name}`, xin hãy nhập lại lần nữa",
                    color=0xf8bbd0
                )
                await interaction.followup.send(embed=embed_none)
                continue

            key = f"{interaction.guild.id}:{emb_name}"
            _cleanup_views(key)

            # Khởi tạo UI Editor
            view = EmbedUIView(interaction.guild.id, emb_name, data, timeout=600.0)
            embed = view.build_embed()

            msg = await interaction.followup.send(
                content=f" **yiyi** mang embed `{emb_name}` về rồi, xin hãy tiếp tục chỉnh sửa {Emojis.YIYITIM}", 
                embed=embed, 
                view=view
            )
            view.message = msg

    @app_commands.command(name="show", description="gửi embed vào channel")
    @app_commands.describe(
        name="chọn embed chính muốn gửi từ danh sách",
        extra_embeds="nhập tên các embed khác muốn gửi kèm, cách nhau bằng dấu phẩy (vd: b, c)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete, extra_embeds=embed_name_autocomplete)
    async def show(self, interaction: discord.Interaction, name: str, extra_embeds: str = None):
        # [KẾT NỐI MẠCH] Gom danh sách các embed cần gửi lần lượt
        embed_names = [name]
        if extra_embeds:
            embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])
            
        await interaction.response.send_message(f"{Emojis.MATTRANG} đang tiến hành gửi lần lượt {len(embed_names)} embed...", ephemeral=True)
        
        for emb_name in embed_names:
            # Nạp dữ liệu từ Cloud Atlas
            data = await load_embed(interaction.guild.id, emb_name)
            if not data: 
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé.",
                    description=f"**yiyi** không tìm thấy embed có tên `{emb_name}`. xin hãy kiểm tra lại bằng `/p embed edit`",
                    color=0xf8bbd0
                )
                await interaction.followup.send(embed=embed_err, ephemeral=True)
                continue
            
            # Giữ nguyên DNA: Tạo View nút bấm linh hoạt cho toàn bộ hệ thống
            view = create_embed_view(data)
            
            # [THỰC THI] Gửi embed thông qua Engine vạn năng
            await send_embed(interaction.channel, data, interaction.guild, interaction.user, embed_name=emb_name, view=view)

    @app_commands.command(name="send", description="gửi embed vào kênh được chỉ định")
    @app_commands.describe(
        channel="chọn kênh muốn gửi embed tới",
        name="chọn embed chính muốn gửi từ danh sách",
        extra_embeds="nhập tên các embed khác muốn gửi kèm, cách nhau bằng dấu phẩy (vd: b, c)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete, extra_embeds=embed_name_autocomplete)
    async def send(self, interaction: discord.Interaction, channel: discord.TextChannel, name: str, extra_embeds: str = None):
        # [KẾT NỐI MẠCH] Logic gửi liên thanh sang channel mục tiêu
        embed_names = [name]
        if extra_embeds:
            embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])
            
        await interaction.response.send_message(f"{Emojis.MATTRANG} đang tiến hành gửi lần lượt {len(embed_names)} embed vào {channel.mention}...", ephemeral=True)
        
        for emb_name in embed_names:
            # Nạp dữ liệu từ Cloud Atlas
            data = await load_embed(interaction.guild.id, emb_name)
            if not data: 
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} aree...hãy thử lại lần nữa nhé.",
                    description=f"**yiyi** không tìm thấy embed có tên `{emb_name}`. xin hãy kiểm tra lại bằng `/p embed edit`",
                    color=0xf8bbd0
                )
                await interaction.followup.send(embed=embed_err, ephemeral=True)
                continue
            
            # Giữ nguyên DNA: Tạo View nút bấm linh hoạt cho toàn bộ hệ thống
            view = create_embed_view(data)
            
            # [THỰC THI] Gửi embed thẳng vào kênh mục tiêu
            await send_embed(channel, data, interaction.guild, interaction.user, embed_name=emb_name, view=view)

    # [LỆNH MỚI] CẬP NHẬT TRỰC TIẾP TIN NHẮN (LIVE SYNC V2 - 1 ĐỔI 1)
    @app_commands.command(name="update", description="cập nhật/sửa lại tin nhắn embed đã gửi bằng link")
    @app_commands.describe(
        message_link="dán link tin nhắn (nếu nhiều link thì cách nhau bằng dấu phẩy)",
        name="chọn embed chính muốn cập nhật từ danh sách",
        extra_embeds="nhập tên các embed khác, cách nhau bằng dấu phẩy (vd: b, c)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete, extra_embeds=embed_name_autocomplete)
    async def update(self, interaction: discord.Interaction, message_link: str, name: str, extra_embeds: str = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. Bóc tách danh sách Link tin nhắn
        links_raw = [l.strip() for l in message_link.split(",") if l.strip()]

        # 2. Gom danh sách Tên embed
        embed_names = [name]
        if extra_embeds:
            embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])

        # Kiểm tra khớp số lượng
        if len(links_raw) != len(embed_names):
            return await interaction.followup.send(
                f"{Emojis.HOICHAM} số lượng link tin nhắn (`{len(links_raw)}`) không khớp với số lượng embed (`{len(embed_names)}`). xin hãy kiểm tra lại!", 
                ephemeral=True
            )

        success_count = 0

        # 3. Chạy vòng lặp bắt cặp 1 Link - 1 Embed
        for link, emb_name in zip(links_raw, embed_names):
            parts = link.strip().split("/")
            try:
                channel_id = int(parts[-2])
                message_id = int(parts[-1])
            except (ValueError, IndexError):
                await interaction.followup.send(f"{Emojis.HOICHAM} link `{link}` không hợp lệ.", ephemeral=True)
                continue

            try:
                channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
                target_msg = await channel.fetch_message(message_id)
            except Exception:
                await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy tin nhắn ở tọa độ link `{link}`.", ephemeral=True)
                continue

            # Load data từ Cloud Atlas
            data = await load_embed(guild.id, emb_name)
            if not data:
                await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không tìm thấy embed có tên `{emb_name}`.", ephemeral=True)
                continue

            # Xây dựng Embed độc lập không qua UI
            data_copy = copy.deepcopy(data)
            if data_copy.get("title") in ["Tiêu đề Embed mới", "tiêu đề embed mới", "embed mới"]:
                data_copy["title"] = "tiêu đề embed mới"
            if data_copy.get("description") in ["Nội dung mô tả mặc định", "Nội dung mô tả mặc định.", "nội dung mô tả mặc định", "nội dung mô tả"]:
                data_copy["description"] = "nội dung mô tả mặc định"
            if data_copy.get("color") in [0x5865f2, 0x5865F2, None]:
                data_copy["color"] = 0xf8bbd0

            data_v = apply_variables(data_copy, guild, interaction.user)
            emb_obj = _build_embed(data_v)
            view = create_embed_view(data)

            # Phẫu thuật đè 1-1 (Xuyên Webhook hoặc Bot)
            try:
                if target_msg.webhook_id:
                    webhooks = await channel.webhooks()
                    webhook = discord.utils.get(webhooks, id=target_msg.webhook_id)
                    if not webhook:
                        await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy webhook quản lý tin nhắn `{link}`.", ephemeral=True)
                        continue
                    
                    await webhook.edit_message(message_id, embed=emb_obj, view=view)
                    success_count += 1
                else:
                    if target_msg.author.id != interaction.client.user.id:
                        await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không thể sửa tin nhắn `{link}` vì nó không phải của bot.", ephemeral=True)
                        continue
                    
                    await target_msg.edit(embed=emb_obj, view=view)
                    success_count += 1
            except Exception as e:
                print(f"[Update Error] {e}", flush=True)
                await interaction.followup.send(f"{Emojis.HOICHAM} phát sinh lỗi khi cập nhật `{emb_name}`: `{e}`", ephemeral=True)

        # Chốt sổ
        if success_count > 0:
            await interaction.followup.send(f"{Emojis.MATTRANG} đã cập nhật thành công {success_count}/{len(embed_names)} tin nhắn!", ephemeral=True)

    @app_commands.command(name="delete", description="xóa embed vĩnh viễn")
    @app_commands.describe(
        name="chọn embed muốn xóa vĩnh viễn từ danh sách",
        extra_embeds="nhập tên các embed khác muốn xoá, cách nhau bằng dấu phẩy (vd: b, c)"
    )
    @app_commands.autocomplete(name=embed_name_autocomplete, extra_embeds=embed_name_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str, extra_embeds: str = None):
        # [QUY TẮC 3S] Defer ngay để giữ kết nối
        await interaction.response.defer(ephemeral=False)
        
        embed_names = [name]
        if extra_embeds:
            embed_names.extend([n.strip() for n in extra_embeds.split(",") if n.strip()])

        # [DEF - TRUY XUẤT DATABASE GỐC] So sánh chuẩn NoneType để tránh crash Motor
        wrapper = getattr(interaction.client, "db", None)
        db = getattr(wrapper, "db", None)

        async def perform_cleanup():
            # 1. Dọn dẹp trong Storage và Views (Xóa dữ liệu RAM và Cloud Embed)
            storage_tasks = [delete_embed(interaction.guild.id, n) for n in embed_names]
            for n in embed_names: 
                _cleanup_views(f"{interaction.guild.id}:{n}")
            
            # [FIX CHÍ MẠNG] Sử dụng 'is not None' thay vì truth value testing
            if db is not None:
                gid = str(interaction.guild.id)
                names_in = {"$in": embed_names}
                
                # 2. [INDUSTRIAL BATCH] Dọn dẹp liên kết ma tại Configs và Forms
                db_tasks = [
                    # Gỡ ở Ticket (Nằm trong configs module ticket)
                    db.configs.update_many(
                        {"guild_id": gid, "module": "ticket", "settings.embed_name": names_in}, 
                        {"$set": {"settings.embed_name": None}}
                    ),
                    # Gỡ ở Forms
                    db.forms.update_many(
                        {"guild_id": gid, "embed_name": names_in}, 
                        {"$set": {"embed_name": None}}
                    ),
                    # Gỡ ở các module Banner hệ thống (configs)
                    db.configs.update_many(
                        {"guild_id": gid, "module": {"$in": ["greet", "leave", "wellcome", "booster"]}, "settings.embed_name": names_in},
                        {"$set": {"settings.embed_name": None}}
                    )
                ]
                await asyncio.gather(*(storage_tasks + db_tasks))
            else:
                await asyncio.gather(*storage_tasks)

        try:
            # Thực thi mạch dọn dẹp tối ưu
            await perform_cleanup()
            
            # 3. BÁO CÁO TỔNG KẾT
            if len(embed_names) > 1:
                await interaction.followup.send(f"{Emojis.MATTRANG} đã xoá thành công `{len(embed_names)}` embed. toàn bộ liên kết tại ticket và hệ thống banner đã được dọn dẹp sạch sẽ.")
            else:
                await interaction.followup.send(f"{Emojis.MATTRANG} embed `{name}` đã được xoá vĩnh viễn và gỡ bỏ liên kết hệ thống.")
        except Exception as e:
            print(f"[Delete Error - Industrial] {e}", flush=True)
            await interaction.followup.send(f"{Emojis.HOICHAM} phát sinh lỗi khi xóa embed: `{e}`")

# =============================
# INJECTION (KHÔI PHỤC MẠCH ĐĂNG KÝ LỆNH CHUẨN)
# =============================

async def setup(bot: commands.Bot):
    # Truy xuất lệnh cha /p từ command tree toàn cục
    p_cmd = bot.tree.get_command("p")
    
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # [CẬP NHẬT] Xóa group cũ trước khi nạp để tránh lỗi lệnh ma khi reload
        existing_embed = next((c for c in p_cmd.commands if c.name == "embed"), None)
        if existing_embed: p_cmd.remove_command("embed")
        
        # 1. Khôi phục nhóm lệnh /p embed ...
        p_cmd.add_command(EmbedGroup())
        print("[load] success: commands.embed.embed_group", flush=True)
        
        # 2. Đăng ký lệnh /p image (Hệ thống CDN)
        if not any(c.name == "image" for c in p_cmd.commands):
            p_cmd.add_command(p_image_cmd)
            print("[load] success: commands.p.image (cdn engine)", flush=True)
    else:
        print("[error] không tìm thấy khung /p! hãy đảm bảo command /p đã được khởi tạo trước.", flush=True)
