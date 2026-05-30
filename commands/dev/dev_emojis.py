#commands/dev/dev_emojis.py
import discord
from discord import app_commands
from discord.ext import commands
import re
import aiohttp
import os
from utils.emojis import Emojis

# CẤU HÌNH SERVER KHO CHỨA TRUNG TÂM TOÀN CỤC NẠP TỪ BIẾN MÔI TRƯỜNG TRƯỚC
VAULT_GUILD_ID = int(os.getenv("VAULT_GUILD_ID", 1439489572936613951))  # <--- Sếp cấu hình ID Server Kho Chứa của sếp tại đây nhe

# =========================================================================
# [NÂNG CẤP INDUSTRIAL] CỖ MÁY PHÂN TRANG (PAGINATION) QUẢN TRỊ
# Kèm mạch Modal tìm trang thông minh và bộ lọc dữ liệu an toàn
# =========================================================================
class PageJumpModal(discord.ui.Modal, title="Tìm kiếm trang tài nguyên"):
    def __init__(self, view):
        super().__init__()
        self.view_ref = view
        self.page_input = discord.ui.TextInput(
            label="Nhập số trang cậu muốn đến",
            placeholder=f"Kho chứa đang có từ 1 đến {self.view_ref.total_pages} trang",
            required=True,
            max_length=4,
            style=discord.TextStyle.short
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.page_input.value.strip()
        
        # Màng lọc 1: Chặn chữ cái, ký tự đặc biệt
        if not val.isdigit():
            return await interaction.response.send_message(f"{Emojis.BUOMA} hông được rồi, cậu phải nhập số nguyên cơ, thử lại nhé.", ephemeral=True)
        
        target = int(val)
        # Màng lọc 2: Chặn số trang ảo (nhỏ hơn 1 hoặc lớn hơn tổng số trang)
        if target < 1 or target > self.view_ref.total_pages:
            return await interaction.response.send_message(f"{Emojis.BUOMA} không có trang {target} đâu, kho chứa hiện chỉ có từ 1 đến {self.view_ref.total_pages} trang thôi cậu.", ephemeral=True)
        
        # Vượt qua màng lọc -> Kích hoạt mạch nhảy trang
        self.view_ref.current_page = target - 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.build_embed(), view=self.view_ref)

class DevEmojiPagination(discord.ui.View):
    def __init__(self, hardcoded_chunks, dynamic_chunks, total_pages):
        super().__init__(timeout=120)
        self.hardcoded_chunks = hardcoded_chunks
        self.dynamic_chunks = dynamic_chunks
        self.total_pages = total_pages
        self.current_page = 0
        self.update_buttons()
        self.message = None

    def update_buttons(self):
        # Tự động khóa nút nếu đang ở đầu hoặc cuối trang
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page == self.total_pages - 1

    def build_embed(self):
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} bảng điều khiển quản lý biến tối cao",
            color=0xe6e2dd
        )
        
        # Hút dữ liệu tương ứng với trang hiện tại
        h_items = self.hardcoded_chunks[self.current_page] if self.current_page < len(self.hardcoded_chunks) else []
        d_items = self.dynamic_chunks[self.current_page] if self.current_page < len(self.dynamic_chunks) else []
        
        h_text = "\n".join(h_items) if h_items else "Trống."
        d_text = "\n".join(d_items) if d_items else "Trống."
        
        embed.add_field(name="[ CORE SYSTEM EMOJIS - HARDCODED IN FILE ]", value=h_text, inline=False)
        embed.add_field(name="[ EXTENDED DEV EMOJIS - DYNAMIC REGISTRY ]", value=d_text, inline=False)
        
        embed.set_footer(text=f"Hệ thống quản lý tài nguyên tối cao của yiyi • Trang {self.current_page + 1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="Trang trước", style=discord.ButtonStyle.secondary, custom_id="prev_page", emoji="◀️")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Chọn trang", style=discord.ButtonStyle.secondary, custom_id="search_page", emoji="🔍")
    async def btn_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Gọi cỗ máy Modal lên cho sếp nhập liệu
        modal = PageJumpModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Trang sau", style=discord.ButtonStyle.secondary, custom_id="next_page", emoji="▶️")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        
    async def on_timeout(self):
        # Tự động hủy nút bấm khi hết thời gian chờ để tiết kiệm RAM
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

class DevEmojis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Mạch bóc tách an toàn để tương thích với mọi cấu trúc Wrapper MongoDB Atlas của hệ thống peiD
        self.db_col = getattr(bot.db, "db", bot.db)["cloud_emojis_sys"]
        # Đấu nối mạch song song đến kho lưu trữ định danh Premium đồng bộ với premium_group.py
        self.premium_col = getattr(bot.db, "db", bot.db)["premium_users_sys"]

    # =========================================================================
    # [QUY HOẠCH CHIẾN LƯỢC] KHỞI TẠO GROUP LỆNH CHUẨN MULTI-IT
    # Khai tử dấu gạch dưới, lấy /dev làm nền tảng cho mọi cấu phần Premium sau này
    # =========================================================================
    dev = app_commands.Group(name="dev", description="[PREMIUM] Bộ điều khiển tối cao dành cho nhà phát triển hệ thống")

    async def has_premium_access(self, interaction: discord.Interaction) -> bool:
        """Mạch bảo mật đối chiếu trực tiếp định danh Thực thể tối cao và sách trắng Premium thời gian thực"""
        if interaction.user.id == interaction.client.boss_id:
            return True
            
        # Mạch truy quét định danh trong sách trắng Premium Atlas DB dựa trên ID người dùng
        premium_user = await self.premium_col.find_one({"user_id": str(interaction.user.id)})
        return premium_user is not None

    def get_unauthorized_embed(self) -> discord.Embed:
        """Mạch kết xuất Giao diện từ chối truy cập chuẩn văn phong mềm mại của yiyi và mã màu sếp yêu cầu"""
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} không được rồi, xin lỗi cậu nhe..",
            description="lệnh này thuộc phân khu Premium, chỉ có owner của **yiyi** hoặc các user được đặc cách mới được sử dụng",
            color=0xe6e2dd
        )
        return embed

    @dev.command(name="register", description="[PREMIUM] đúc emoji vào kho chứa thực thể và cấy nóng thành biến hệ thống")
    @app_commands.describe(
        variable_name="tên biến muốn gọi trong code (vd: alert, peid_omg)",
        emoji_input="dán emoji, nhập id số, HOẶC dán link ảnh/gif (http...)"
    )
    async def dev_register_cmd(self, interaction: discord.Interaction, variable_name: str, emoji_input: str):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not await self.has_premium_access(interaction):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        var_name_clean = variable_name.strip().upper()
        input_clean = emoji_input.strip()

        # Mạch kiểm toán chống ghi đè
        existing = await self.db_col.find_one({"custom_name": var_name_clean})
        if existing:
            embed_dup = discord.Embed(
                title=f"{Emojis.BUOMA} biến này đã tồn tại",
                description=f"tên biến `{var_name_clean}` đã có trong bộ nhớ dynamic hệ thống, hãy nhập tên khác nhé.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_dup)

        # =========================================================================
        # 1. LÕI HẤP THỤ ĐA DẢI (OMNI-INPUT PARSER)
        # =========================================================================
        is_direct_url = input_clean.startswith("http://") or input_clean.startswith("https://")
        is_animated = None
        emoji_id = None
        fetch_urls = []

        if is_direct_url:
            # Nhánh 1: Nuốt trọn mọi loại link (Trực tiếp hoặc Proxy qua lệnh)
            fetch_urls.append(input_clean)
        else:
            # Nhánh 2: Bóc tách cấu trúc Emoji hoặc ID thô
            emoji_match = re.search(r'<(a)?:[A-Za-z0-9_]+:(\d+)>', input_clean)
            if emoji_match:
                is_animated = bool(emoji_match.group(1))
                emoji_id = emoji_match.group(2)
                ext = "gif" if is_animated else "png"
                fetch_urls.append(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
            else:
                emoji_id = "".join(filter(str.isdigit, input_clean))
                if emoji_id:
                    # Kích hoạt Thử Nghiệm Kép cho ID mù
                    fetch_urls.append(f"https://cdn.discordapp.com/emojis/{emoji_id}.gif")
                    fetch_urls.append(f"https://cdn.discordapp.com/emojis/{emoji_id}.png")
                else:
                    return await interaction.followup.send(embed=discord.Embed(
                        title=f"{Emojis.HOICHAM} đầu vào không hợp lệ",
                        description="cậu hãy dán đúng thực thể emoji, chuỗi id số, hoặc link url hợp lệ nhe.",
                        color=0xe6e2dd
                    ))

        # =========================================================================
        # 2. KHỞI CHẠY RADAR HÚT DỮ LIỆU & KIỂM ĐỊNH (ATK/DEF ENGINE)
        # =========================================================================
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        img_bytes = None
        content_type = ""
        diagnostic_msg = "Không thể kết nối đến máy chủ mạng hoặc bị hạ tầng bảo mật chặn."

        async with aiohttp.ClientSession(headers=headers) as session:
            for url in fetch_urls:
                try:
                    async with session.get(url, timeout=15) as response:
                        if response.status == 200:
                            img_bytes = await response.read()
                            content_type = response.headers.get("Content-Type", "").lower()
                            break
                        elif response.status in [403, 404]:
                            diagnostic_msg = f"Đường dẫn bị từ chối truy cập hoặc file gốc đã bị xóa (Mã lỗi: {response.status})."
                except Exception as e:
                    diagnostic_msg = f"Ngắt kết nối đột ngột: `{str(e)}`"
                    continue

        # Màng lọc 1: Trượt dữ liệu
        if not img_bytes:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} không thể thu thập asset",
                description=f"quá trình tải gói dữ liệu ảnh thô thất bại.\n↳ **Nguyên nhân:** {diagnostic_msg}",
                color=0xe6e2dd
            ))

        # Màng lọc 2: Định dạng rác (HTML/Text)
        if "html" in content_type or "text" in content_type:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} định dạng gói tin sai lệch",
                description="link cậu cung cấp trỏ đến một trang web chứ không phải dữ liệu ảnh/gif thô. Cậu hãy copy đúng *'địa chỉ hình ảnh (image url)'* nhe.",
                color=0xe6e2dd
            ))

        # Màng lọc 3: Cân điện tử giới hạn dung lượng
        file_size_kb = len(img_bytes) / 1024
        if file_size_kb > 256:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} gói dữ liệu bị quá tải",
                description=f"kích thước tài nguyên lên tới `{file_size_kb:.1f} KB`, vượt quá giới hạn cho phép là `256 KB` của lõi Discord. Cậu nén lại chút nha.",
                color=0xe6e2dd
            ))

        # Phân giải trạng thái hoạt họa cho nhóm URL và Fallback
        if is_direct_url:
            if "gif" in content_type or ".gif" in input_clean.lower():
                is_animated = True
            else:
                is_animated = False
        elif emoji_id and is_animated is None:
            if "gif" in content_type:
                is_animated = True
            else:
                is_animated = False

        # =========================================================================
        # 3. GIAO TIẾP VỚI KHO CHỨA & ĐÚC THỰC THỂ BẤT TỬ
        # =========================================================================
        vault_guild = self.bot.get_guild(VAULT_GUILD_ID)
        if not vault_guild:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} mất liên lạc với kho chứa",
                description="hệ thống không tìm thấy server Kho Chứa Trung Tâm, cậu hãy kiểm tra lại cấu hình ID nhé.",
                color=0xe6e2dd
            ))

        try:
            new_emoji = await vault_guild.create_custom_emoji(
                name=f"sys_{var_name_clean.lower()}",
                image=img_bytes,
                reason=f"Kích hoạt đúc biến hệ thống bởi {interaction.user.name}"
            )
        except discord.Forbidden:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} thiếu quyền hạn tại kho",
                description="yiyi hiện không có quyền `Quản lý Emoji` trong Server Kho Chứa, cậu cấp quyền lại cho tớ nhe.",
                color=0xe6e2dd
            ))
        except discord.HTTPException as e:
            # Mã định danh lỗi 30008: Bị đầy slot emoji
            if e.code == 30008:
                return await interaction.followup.send(embed=discord.Embed(
                    title=f"{Emojis.HOICHAM} kho chứa đã bão hòa",
                    description="server Kho Chứa hiện tại không còn slot trống để đúc thêm emoji. Cậu cần xóa bớt hoặc quy hoạch kho mới.",
                    color=0xe6e2dd
                ))
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} discord từ chối vận hành",
                description=f"nghẽn mạch nội bộ tại khâu đúc API: `{e.text}`",
                color=0xe6e2dd
            ))

        # 4. Lưu trữ Database và Nạp RAM nóng
        try:
            data_document = {
                "custom_name": var_name_clean,
                "vault_emoji_id": str(new_emoji.id),
                "original_name": new_emoji.name,
                "is_animated": is_animated
            }
            await self.db_col.insert_one(data_document)

            # Cấy nóng biến thời gian thực
            emoji_string = f"<a:{new_emoji.name}:{new_emoji.id}>" if is_animated else f"<:{new_emoji.name}:{new_emoji.id}>"
            setattr(Emojis, var_name_clean, emoji_string)

            embed_success = discord.Embed(
                title=f"{Emojis.BUOMA} đăng ký biến động thành công!",
                description=f"đã cấy thuộc tính `{var_name_clean}` vào hệ thống biến emojis.\n\n"
                            f"• **Hình ảnh hiển thị:** {emoji_string}\n"
                            f"• **Mã gọi trong mã nguồn:** `Emojis.{var_name_clean}`",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed_success)
        except Exception as e:
            # Mạch hoàn tác (Rollback): Nếu DB đám mây sập, xóa ngay emoji vừa đúc để tránh rác slot kho chứa
            await new_emoji.delete(reason="Lõi DB sập, hoàn tác quy trình đúc rác")
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} đứt gãy kết nối đám mây",
                description=f"đã đúc thành công nhưng máy chủ cơ sở dữ liệu từ chối lưu. Lỗi phát sinh: `{str(e)}`\n*(Hệ thống đã tự động hoàn tác để giải phóng slot kho)*",
                color=0xe6e2dd
            ))

    @dev.command(name="list", description="[PREMIUM] soi chiếu toàn bộ bảng biến mã nguồn tĩnh vật lý và động")
    async def dev_list_cmd(self, interaction: discord.Interaction):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not await self.has_premium_access(interaction):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # 2. Truy quét toàn bộ danh sách định danh biến động đã lưu trữ dưới MongoDB Atlas đám mây trước
        dynamic_list = []
        dynamic_keys = set()  # [MẠCH NÂNG CẤP RANH GIỚI] Lưu cache tên để lọc loại trừ triệt để
        async for item in self.db_col.find({}):
            # [VÁ LỖI AN TOÀN] Dùng .get() để né đòn KeyError nếu DB có bản ghi bị lỗi
            v_id = item.get("vault_emoji_id")
            o_name = item.get("original_name")
            if not v_id or not o_name: 
                continue
                
            fmt = f"<a:{o_name}:{v_id}>" if item.get("is_animated") else f"<:{o_name}:{v_id}>"
            dynamic_list.append(f"• `{item.get('custom_name')}` ──> {fmt}")
            dynamic_keys.add(item.get("custom_name"))

        # 1. Thuật toán Phản Chiếu (Reflection): Quét sạch và bóc tách toàn bộ biến cứng trong file vật lý utils/emojis.py
        hardcoded_list = []
        for attr, val in Emojis.__dict__.items():
            if not attr.startswith("__") and isinstance(val, str):
                # Ranh giới sạch sẽ tuyệt đối: Nếu biến đã được cấy động từ database thì bỏ qua không in vào khu file cứng
                if attr.upper() not in dynamic_keys:
                    hardcoded_list.append(f"• `{attr}` ──> {val}")

        # ==========================================================
        # [KÍCH HOẠT CỖ MÁY PAGINATION] Đóng gói và Phân trang 
        # ==========================================================
        def chunk_list(lst, n):
            return [lst[i:i + n] for i in range(0, len(lst), n)]
            
        # Mỗi trang chỉ chứa 15 biến, đảm bảo dung lượng Field luôn nhỏ hơn 600 ký tự (Chấp 1024)
        hard_chunks = chunk_list(hardcoded_list, 15) or [[]]
        dyn_chunks = chunk_list(dynamic_list, 15) or [[]]
        total_pages = max(len(hard_chunks), len(dyn_chunks))

        if total_pages <= 1:
            # Dựng Dashboard một trang duy nhất không cần nút bấm
            embed_dashboard = discord.Embed(
                title=f"{Emojis.BUOMA} bảng điều khiển quản lý biến tối cao",
                color=0xe6e2dd
            )
            
            h_text = "\n".join(hard_chunks[0]) if hard_chunks[0] else "Trống."
            d_text = "\n".join(dyn_chunks[0]) if dyn_chunks[0] else "Chưa có biến động nào được cấy vào database."
            
            embed_dashboard.add_field(name="[ CORE SYSTEM EMOJIS - HARDCODED IN FILE ]", value=h_text, inline=False)
            embed_dashboard.add_field(name="[ EXTENDED DEV EMOJIS - DYNAMIC REGISTRY ]", value=d_text, inline=False)
            embed_dashboard.set_footer(text="Hệ thống quản lý tài nguyên tối cao của yiyi")
            
            await interaction.followup.send(embed=embed_dashboard)
        else:
            # Kích hoạt Cỗ máy UI Phân trang
            view = DevEmojiPagination(hard_chunks, dyn_chunks, total_pages)
            msg = await interaction.followup.send(embed=view.build_embed(), view=view)
            view.message = msg

    # =========================================================================
    # [CẤY MỚI HOÀN TOÀN] MẠCH HỦY TÀI NGUYÊN VÀ GIẢI PHÓNG BỘ NHỚ RAM TỐI CAO
    # Tự động dọn dẹp thực thể tại Vault Server, gỡ DB và trục xuất hoàn toàn khỏi RAM
    # =========================================================================
    @dev.command(name="delete", description="[PREMIUM] xóa sổ biến động khỏi cơ sở dữ liệu, kho chứa và giải phóng bộ nhớ RAM")
    @app_commands.describe(variable_name="tên biến dynamic sếp muốn xóa sổ (vd: alert, peid_omg)")
    async def dev_delete_cmd(self, interaction: discord.Interaction, variable_name: str):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not await self.has_premium_access(interaction):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        var_name_clean = variable_name.strip().upper()

        # Kiểm toán sự tồn tại: Tìm bản ghi định vị thực thể trong MongoDB Atlas
        target_emoji = await self.db_col.find_one({"custom_name": var_name_clean})
        if not target_emoji:
            embed_not_found = discord.Embed(
                title=f"{Emojis.HOICHAM} không tìm thấy biến này",
                description=f"biến `{var_name_clean}` không tồn tại trong danh mục biến động hệ thống.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_not_found)

        errors_log = []
        vault_emoji_id = target_emoji["vault_emoji_id"]

        # 1. Mạch giải phóng tài nguyên thực thể: Mò vào Server Kho Chứa gỡ bỏ emoji để thu hồi slot trống
        try:
            vault_guild = self.bot.get_guild(VAULT_GUILD_ID)
            if vault_guild:
                # Tìm nạp thực thể sống của emoji để xóa sổ qua API Discord
                emoji_obj = discord.utils.get(vault_guild.emojis, id=int(vault_emoji_id))
                if not emoji_obj:
                    # Nếu cache rỗng, kích hoạt mạch nạp cưỡng bức để truy tìm tận gốc
                    try:
                        emoji_obj = await vault_guild.fetch_emoji(int(vault_emoji_id))
                    except:
                        emoji_obj = None
                
                if emoji_obj:
                    # Vá lỗi: Gọi hàm delete trực tiếp lên đối tượng emoji theo chuẩn discord.py
                    await emoji_obj.delete(reason=f"Mạch dọn dẹp tự động qua lệnh /dev delete bởi {interaction.user}")
                else:
                    errors_log.append("Thực thể emoji không còn tồn tại trên Server Kho Chứa (có thể đã bị xóa thủ công).")
            else:
                errors_log.append("Không thể tiếp cận Server Kho Chứa để dọn dẹp thực thể slot.")
        except Exception as e:
            errors_log.append(f"Mạch gỡ thực thể dính lỗi phát sinh: {str(e)}")

        # 2. Mạch xóa sổ dữ liệu: Loại bỏ vĩnh viễn bản ghi khỏi bộ nhớ MongoDB đám mây
        await self.db_col.delete_one({"custom_name": var_name_clean})

        # 3. Mạch trục xuất RAM: Trục xuất thuộc tính động khỏi Class Emojis thời gian thực
        if hasattr(Emojis, var_name_clean):
            delattr(Emojis, var_name_clean)

        # 4. Xuất Embed báo cáo kết quả chuẩn gam màu và văn phong yiyi
        desc_msg = f"đã trục xuất biến `{var_name_clean}` ra khỏi bộ nhớ RAM và cơ sở dữ liệu thành công rồi cậu."
        if errors_log:
            desc_msg += f"\n\n⚠️ **Lưu ý trong quá trình dọn kho bãi:**\n- " + "\n- ".join(errors_log)

        embed_del_success = discord.Embed(
            title=f"{Emojis.BUOMA} xóa sổ biến động thành công!",
            description=desc_msg,
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_del_success)

async def load_dynamic_emojis(bot):
    """Hàm lõi đồng bộ hóa: Hút toàn bộ biến động từ MongoDB và nạp đè vào RAM khi khởi động bot"""
    db_col = getattr(bot.db, "db", bot.db)["cloud_emojis_sys"]
    async for item in db_col.find({}):
        # [VÁ LỖI AN TOÀN] Dùng .get() để cỗ máy không sập nếu rỗng data
        var_name = item.get("custom_name")
        v_id = item.get("vault_emoji_id")
        o_name = item.get("original_name")
        
        if not var_name or not v_id or not o_name: 
            continue
            
        emoji_string = f"<a:{o_name}:{v_id}>" if item.get("is_animated") else f"<:{o_name}:{v_id}>"
        setattr(Emojis, var_name, emoji_string)
    print(f"[LOADED] Success: Đã đồng bộ toàn bộ biến emoji động hệ Premium vào RAM bộ nhớ!", flush=True)

async def setup(bot: commands.Bot):
    # [VÁ LỖI CẤP CAO] Bơm đạn lên RAM trước khi nạp Cog để hệ thống không bị "quên" biến
    await load_dynamic_emojis(bot)
    
    await bot.add_cog(DevEmojis(bot))
    print("[LOAD] Success: commands.dev.dev_emojis (Premium Dev Edition Loaded - Multi-URL Engine & Diagnostic Injected)", flush=True)
