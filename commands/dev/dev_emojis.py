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

    def is_owner(self, interaction: discord.Interaction) -> bool:
        """Mạch bảo mật đối chiếu trực tiếp định danh Thực thể tối cao (Owner ID) thời gian thực"""
        return interaction.user.id == interaction.client.boss_id

    def get_unauthorized_embed(self) -> discord.Embed:
        """Mạch kết xuất Giao diện từ chối truy cập chuẩn văn phong mềm mại của yiyi và mã màu sếp yêu cầu"""
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} không được rồi, xin lỗi cậu nhe..",
            description="lệnh này chỉ có owner của *yiyi* mới được sài thuii",
            color=0xe6e2dd
        )
        return embed

    @app_commands.command(name="dev_register", description="[PREMIUM] đúc emoji vào kho chứa thực thể và cấy nóng thành biến hệ thống")
    @app_commands.describe(
        variable_name="tên biến muốn gọi trong code (vd: alert, peid_omg)",
        emoji_input="dán emoji trực tiếp hoặc nhập chuỗi id số của emoji gốc"
    )
    async def dev_register_cmd(self, interaction: discord.Interaction, variable_name: str, emoji_input: str):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not self.is_owner(interaction):
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
                title=f"{Emojis.BUOMA} đầu vào không hợp lệ rồi nhe sếp",
                description="cậu hãy dán đúng thực thể emoji hoặc nhập đúng chuỗi id số nhe.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed_err)

        # Mạch kiểm toán chống ghi đè: Truy quét sự tồn tại của tên biến trong Database đám mây
        existing = await self.db_col.find_one({"custom_name": var_name_clean})
        if existing:
            embed_dup = discord.Embed(
                title=f"{Emojis.BUOMA} biến này đã tồn tại",
                description=f"tên biến `{var_name_clean}` đã có trong bộ nhớ dynamic hệ thống rồi cậu.",
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
                description=f"đã cấy thuộc tính `{var_name_clean}` vào hệ thống lõi vĩnh viễn nhe sếp.\n\n"
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

    @app_commands.command(name="dev_list", description="[PREMIUM] soi chiếu toàn bộ bảng biến mã nguồn tĩnh vật lý và động")
    async def dev_list_cmd(self, interaction: discord.Interaction):
        # Bộ lọc an toàn tối cao chặn đứng các thực thể không hợp lệ
        if not self.is_owner(interaction):
            return await interaction.response.send_message(embed=self.get_unauthorized_embed(), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # 1. Thuật toán Phản Chiếu (Reflection): Quét sạch và bóc tách toàn bộ biến cứng trong file vật lý utils/emojis.py
        hardcoded_list = []
        for attr, val in Emojis.__dict__.items():
            if not attr.startswith("__") and isinstance(val, str):
                hardcoded_list.append(f"• `{attr}` ──> {val}")

        # 2. Truy quét toàn bộ danh sách định danh biến động đã lưu trữ dưới MongoDB Atlas đám mây
        dynamic_list = []
        async for item in self.db_col.find({}):
            v_id = item["vault_emoji_id"]
            o_name = item["original_name"]
            fmt = f"<a:{o_name}:{v_id}>" if item["is_animated"] else f"<:{o_name}:{v_id}>"
            dynamic_list.append(f"• `{item['custom_name']}` ──> {fmt}")

        # 3. Dựng Dashboard điều khiển phân khu hiển thị đồ họa trực quan chi tiết
        embed_dashboard = discord.Embed(
            title=f"{Emojis.BUOMA} bảng điều khiển quản lý biến tối cao",
            color=0xe6e2dd
        )
        
        # Phòng vệ giới hạn ký tự (Giới hạn 1024 của field Discord): Cắt chuỗi thông minh nếu số lượng biến quá lớn
        h_text = "\n".join(hardcoded_list) if hardcoded_list else "Trống."
        if len(h_text) > 1024: 
            h_text = h_text[:1000] + "\n...và một số biến hệ thống khác"
        embed_dashboard.add_field(name="[ CORE SYSTEM EMOJIS - HARDCODED IN FILE ]", value=h_text, inline=False)

        d_text = "\n".join(dynamic_list) if dynamic_list else "Chưa có biến động nào được cấy vào database."
        if len(d_text) > 1024: 
            d_text = d_text[:1000] + "\n...và một số biến động khác"
        embed_dashboard.add_field(name="[ EXTENDED DEV EMOJIS - DYNAMIC REGISTRY ]", value=d_text, inline=False)

        embed_dashboard.set_footer(text="Hệ thống quản lý tài nguyên tối cao của yiyi")
        await interaction.followup.send(embed=embed_dashboard)

async def load_dynamic_emojis(bot):
    """Hàm lõi đồng bộ hóa: Hút toàn bộ biến động từ MongoDB và nạp đè vào RAM khi khởi động bot"""
    db_col = getattr(bot.db, "db", bot.db)["cloud_emojis_sys"]
    async for item in db_col.find({}):
        var_name = item["custom_name"]
        v_id = item["vault_emoji_id"]
        o_name = item["original_name"]
        emoji_string = f"<a:{o_name}:{v_id}>" if item["is_animated"] else f"<:{o_name}:{v_id}>"
        setattr(Emojis, var_name, emoji_string)
    print(f"[LOADED] Success: Đã đồng bộ toàn bộ biến emoji động hệ Premium vào RAM bộ nhớ!", flush=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DevEmojis(bot))
    print("[LOAD] Success: commands.dev.dev_emojis (Premium Dev Edition Loaded)", flush=True)
