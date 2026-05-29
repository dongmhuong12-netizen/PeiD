import discord
from discord import app_commands
from discord.ext import commands
import re
import aiohttp
import os
from utils.emojis import Emojis

# CẤU HÌNH SERVER KHO CHỨA TRUNG TÂM TOÀN CỤC NẠP TỪ BIẾN MÔI TRƯỜNG TRƯỚC
VAULT_GUILD_ID = int(os.getenv("VAULT_GUILD_ID", 1439489572936613951))  # <--- Sếp cấu hình ID Server Kho Chứa của sếp tại đây nhe

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
        emoji_input="dán emoji trực tiếp hoặc nhập chuỗi id số của emoji gốc"
    )
    async def dev_register_cmd(self, interaction: discord.Interaction, variable_name: str, emoji_input: str):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not await self.has_premium_access(interaction):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        var_name_clean = variable_name.strip().upper()

        # Bộ lọc Regex phân tách cấu trúc đồ họa thô (ID và Trạng thái hoạt ảnh) của Emoji đầu vào
        emoji_match = re.search(r'<(a)?:[A-Za-z0-9_]+:(\d+)>', emoji_input)
        if emoji_match:
            is_animated = bool(emoji_match.group(1))
            emoji_id = emoji_match.group(2)
        else:
            # Thuật toán dự phòng lọc chuỗi số nguyên nếu sếp chỉ nhập ID thô
            emoji_id = "".join(filter(str.isdigit, emoji_input))
            is_animated = False

        if not emoji_id:
            embed_err = discord.Embed(
                title=f"{Emojis.BUOMA} đầu vào không hợp lệ",
                description="cậu hãy dán đúng thực thể emoji hoặc nhập đúng chuỗi id số nhe.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)

        # Mạch kiểm toán chống ghi đè: Truy quét sự tồn tại của tên biến trong Database đám mây
        existing = await self.db_col.find_one({"custom_name": var_name_clean})
        if existing:
            embed_dup = discord.Embed(
                title=f"{Emojis.BUOMA} biến này đã tồn tại",
                description=f"tên biến `{var_name_clean}` đã có trong bộ nhớ dynamic hệ thống, hãy nhập tên khác nhé.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_dup)

        # Thiết lập đường truyền và kết nối CDN Discord toàn cầu để hút asset thô về RAM tạm thời
        ext = "gif" if is_animated else "png"
        cdn_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(cdn_url) as response:
                    if response.status != 200:
                        raise Exception("Mạng lưới hạ tầng CDN Discord từ chối phản hồi gói dữ liệu ảnh thô")
                    img_bytes = await response.read()

            # Tiếp cận Server Kho Chứa Trung Tâm để đúc thực thể emoji bất tử
            vault_guild = self.bot.get_guild(VAULT_GUILD_ID)
            if not vault_guild:
                raise Exception("Bot không có mặt trong Server Kho Chứa Trung Tâm hoặc cấu hình sai ID Guild")

            new_emoji = await vault_guild.create_custom_emoji(
                name=f"sys_{var_name_clean.lower()}",
                image=img_bytes
            )

            # Đồng bộ hóa cấu trúc dữ liệu bản đồ định danh xuống MongoDB Atlas
            data_document = {
                "custom_name": var_name_clean,
                "vault_emoji_id": str(new_emoji.id),
                "original_name": new_emoji.name,
                "is_animated": is_animated
            }
            await self.db_col.insert_one(data_document)

            # =========================================================================
            # [CẤY NÓNG BIẾN THỜI GIAN THỰC ĐỘC QUYỀN PREMIUM]
            # Nạp thẳng thuộc tính vào class Emojis trong bộ nhớ RAM ngay tại runtime.
            # Giúp sếp viết code gọi biến dùng được luôn ở các file khác mà không cần reboot bot.
            # =========================================================================
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
            embed_fail = discord.Embed(
                title=f"{Emojis.BUOMA} nghẽn mạch khi xử lý đúc asset",
                description=f"lỗi phát sinh trong quá trình vận hành ngầm của cỗ máy: `{str(e)}`",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed_fail)

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

        # 3. Dựng Dashboard điều khiển phân khu hiển thị đồ họa trực quan chi tiết
        embed_dashboard = discord.Embed(
            title=f"{Emojis.BUOMA} bảng điều khiển quản lý biến tối cao",
            color=0xe6e2dd
        )
        
        # [THUẬT TOÁN ĐÓNG GÓI AN TOÀN] Cân đo đong đếm, tuyệt đối không chém đứt nửa chừng mã emoji
        def build_safe_field(items, empty_msg, max_len=950):
            res = ""
            for idx, item in enumerate(items):
                if len(res) + len(item) + 1 > max_len:
                    res += f"\n*...và {len(items) - idx} biến khác đang ẩn*"
                    break
                res += item + "\n"
            return res.strip() if res else empty_msg

        h_text = build_safe_field(hardcoded_list, "Trống.")
        d_text = build_safe_field(dynamic_list, "Chưa có biến động nào được cấy vào database.")

        embed_dashboard.add_field(name="[ CORE SYSTEM EMOJIS - HARDCODED IN FILE ]", value=h_text, inline=False)
        embed_dashboard.add_field(name="[ EXTENDED DEV EMOJIS - DYNAMIC REGISTRY ]", value=d_text, inline=False)

        embed_dashboard.set_footer(text="Hệ thống quản lý tài nguyên tối cao của yiyi")
        await interaction.followup.send(embed=embed_dashboard)

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
                title=f"{Emojis.BUOMA} không tìm thấy biến này",
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
    print("[LOAD] Success: commands.dev.dev_emojis (Premium Dev Edition Loaded)", flush=True)
