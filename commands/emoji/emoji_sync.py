import discord
from discord import app_commands
from discord.ext import commands
import re
import aiohttp
import asyncio
from utils.emojis import Emojis

class EmojiSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tương thích với cấu trúc MongoDB Atlas của peiD
        self.db_col = getattr(bot.db, "db", bot.db)["user_emoji_packs"]

    # =========================================================================
    # KHỞI TẠO GROUP LỆNH CHUẨN MULTI-IT
    # =========================================================================
    emoji = app_commands.Group(name="emoji", description="hệ thống quản lý và đồng bộ kho emoji cá nhân")

    # [1] LỆNH COPY LẺ
    @emoji.command(name="copy", description="sao chép 1 emoji vào gói lưu trữ cá nhân")
    @app_commands.describe(
        pack_name="tên gói lưu trữ (vd: meme, yiyi_cute)",
        emoji_input="dán emoji trực tiếp hoặc nhập id emoji"
    )
    async def emoji_copy(self, interaction: discord.Interaction, pack_name: str, emoji_input: str):
        await interaction.response.defer(ephemeral=True)
        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)

        emoji_match = re.search(r'<(a)?:([A-Za-z0-9_]+):(\d+)>', emoji_input)
        if emoji_match:
            is_animated = bool(emoji_match.group(1))
            e_name = emoji_match.group(2)
            e_id = emoji_match.group(3)
        else:
            e_id = "".join(filter(str.isdigit, emoji_input))
            e_name = f"emoji_{e_id}"
            is_animated = False

        if not e_id:
            return await interaction.followup.send(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} đầu vào không hợp lệ",
                description="cậu hãy dán đúng emoji hoặc id nhé.",
                color=0xe6e2dd
            ))

        ext = "gif" if is_animated else "png"
        cdn_url = f"https://cdn.discordapp.com/emojis/{e_id}.{ext}"
        source_guild = interaction.guild.name if interaction.guild else "Mất dấu máy chủ (DM)"

        # Tìm STT lớn nhất hiện tại trong gói để cộng dồn
        max_doc = await self.db_col.find({"user_id": user_id_str, "pack_name": pack_clean}).sort("stt", -1).limit(1).to_list(1)
        next_stt = (max_doc[0]["stt"] + 1) if max_doc else 1

        data_doc = {
            "user_id": user_id_str,
            "pack_name": pack_clean,
            "source_guild_name": source_guild,
            "stt": next_stt,
            "emoji_id": e_id,
            "emoji_name": e_name,
            "emoji_url": cdn_url,
            "is_animated": is_animated
        }
        await self.db_col.insert_one(data_doc)

        embed = discord.Embed(
            title=f"{Emojis.BUOMA} đã lưu vào gói `{pack_clean}`",
            description=f"đã đóng gói thành công ở vị trí số **{next_stt}**.\n\n• Nguồn: `{source_guild}`\n• Ký danh: `{e_name}`",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    # [2] LỆNH COPY TOÀN BỘ SERVER
    @emoji.command(name="copy_all", description="sao chép toàn bộ emoji của máy chủ hiện tại vào gói")
    @app_commands.describe(pack_name="tên gói lưu trữ")
    async def emoji_copy_all(self, interaction: discord.Interaction, pack_name: str):
        if not interaction.guild:
            return await interaction.response.send_message("lệnh này chỉ dùng được trong máy chủ thôi cậu.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        guild_emojis = interaction.guild.emojis
        if not guild_emojis:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.HOICHAM} máy chủ này không có emoji, **yiyi** hong copy được.", color=0xe6e2dd
            ))

        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)
        
        max_doc = await self.db_col.find({"user_id": user_id_str, "pack_name": pack_clean}).sort("stt", -1).limit(1).to_list(1)
        current_stt = (max_doc[0]["stt"]) if max_doc else 0

        docs_to_insert = []
        for e in guild_emojis:
            current_stt += 1
            ext = "gif" if e.animated else "png"
            docs_to_insert.append({
                "user_id": user_id_str,
                "pack_name": pack_clean,
                "source_guild_name": interaction.guild.name,
                "stt": current_stt,
                "emoji_id": str(e.id),
                "emoji_name": e.name,
                "emoji_url": f"https://cdn.discordapp.com/emojis/{e.id}.{ext}",
                "is_animated": e.animated
            })

        if docs_to_insert:
            await self.db_col.insert_many(docs_to_insert)

        embed = discord.Embed(
            title=f"{Emojis.BUOMA} sao chép toàn bộ emoji thành công",
            description=f"đã đóng gói **{len(docs_to_insert)}** emoji của `{interaction.guild.name}` vào gói `{pack_clean}`.",
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed)

    # [3] LỆNH XEM KHO (BẢO HIỂM UI/UX)
    @emoji.command(name="list", description="xem danh sách các gói hoặc chi tiết một gói")
    @app_commands.describe(pack_name="tên gói cần soi (bỏ trống để xem tổng quan các gói)")
    async def emoji_list(self, interaction: discord.Interaction, pack_name: str = None):
        await interaction.response.defer(ephemeral=True)
        user_id_str = str(interaction.user.id)

        if not pack_name:
            # Danh sách tổng quan
            pipeline = [
                {"$match": {"user_id": user_id_str}},
                {"$group": {"_id": "$pack_name", "count": {"$sum": 1}}}
            ]
            cursor = self.db_col.aggregate(pipeline)
            packs = await cursor.to_list(length=None)
            
            if not packs:
                return await interaction.followup.send(embed=discord.Embed(
                    description=f"{Emojis.BUOMA} **yiyi** chưa có emoji vào trong bộ nhớ, cậu hãy dùng `/emoji copy` nhé.", color=0xe6e2dd
                ))
            
            desc = "\n".join([f"📦 **{p['_id']}** ── chứa `{p['count']}` emoji" for p in packs])
            embed = discord.Embed(title="kho lưu trữ cá nhân", description=desc, color=0xe6e2dd)
            return await interaction.followup.send(embed=embed)

        # Chi tiết một gói
        pack_clean = pack_name.strip().lower()
        cursor = self.db_col.find({"user_id": user_id_str, "pack_name": pack_clean}).sort("stt", 1)
        items = await cursor.to_list(length=None)

        if not items:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.BUOMA} gói {pack_clean} trống hoặc không tồn tại.", color=0xe6e2dd
            ))

        lines = []
        source_set = set()
        for item in items:
            source_set.add(item.get("source_guild_name", "Không rõ"))
            emoji_obj = self.bot.get_emoji(int(item["emoji_id"]))
            
            # Mạch phân nhánh render đồ họa vs hyper-link
            if emoji_obj:
                lines.append(f"`{item['stt']:02d}.` {emoji_obj} ── `{item['emoji_name']}`")
            else:
                lines.append(f"`{item['stt']:02d}.` [🖼️ Xem Ảnh]({item['emoji_url']}) ── `{item['emoji_name']}`")

        desc = "\n".join(lines)
        if len(desc) > 4000:
            desc = desc[:3950] + "\n\n*(...danh sách quá dài, một số mục đã bị ẩn)*"

        embed = discord.Embed(title=f"chi tiết gói: {pack_clean}", description=desc, color=0xe6e2dd)
        embed.set_footer(text=f"Nguồn gốc: {', '.join(list(source_set)[:3])}")
        await interaction.followup.send(embed=embed)

    # [4] LỆNH PASTE LẺ
    @emoji.command(name="paste", description="đúc 1 emoji từ gói vào máy chủ hiện tại")
    @app_commands.describe(pack_name="tên gói", stt="số thứ tự của emoji")
    async def emoji_paste(self, interaction: discord.Interaction, pack_name: str, stt: int):
        if not interaction.guild:
            return await interaction.response.send_message("lệnh này cần dùng trong máy chủ cậu nha.", ephemeral=True)
            
        # Kiểm tra quyền hạn kép
        if not interaction.user.guild_permissions.manage_emojis or not interaction.guild.me.guild_permissions.manage_emojis:
            return await interaction.response.send_message(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} aree...? có lỗi gì đó ở đây",
                description="**yiyi** hoặc cậu bị thiếu gì trong máy chủ này, hãy kiểm tra lại quyền trước khi dùng lệnh nhé",
                color=0xe6e2dd
            ), ephemeral=True)

        await interaction.response.defer()
        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)

        item = await self.db_col.find_one({"user_id": user_id_str, "pack_name": pack_clean, "stt": stt})
        if not item:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.BUOMA} không tìm thấy emoji số `{stt}` trong gói `{pack_clean}`.", color=0xe6e2dd
            ))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(item["emoji_url"]) as resp:
                    if resp.status != 200:
                        raise Exception("không hút được ảnh từ CDN")
                    img_bytes = await resp.read()

            new_emoji = await interaction.guild.create_custom_emoji(name=item["emoji_name"], image=img_bytes)
            await interaction.followup.send(f"đã tái bản emoji {new_emoji} vào máy chủ thành công.")
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(
                description=f"quá trình tái bản bị gián đoạn: {e}", color=0xe6e2dd
            ))

    # [5] LỆNH PASTE CẢ GÓI
    @emoji.command(name="paste_pack", description="đúc toàn bộ emoji trong gói vào máy chủ hiện tại")
    @app_commands.describe(pack_name="tên gói")
    async def emoji_paste_pack(self, interaction: discord.Interaction, pack_name: str):
        if not interaction.guild:
            return await interaction.response.send_message("lệnh này cần dùng trong máy chủ cậu nha.", ephemeral=True)
            
        if not interaction.user.guild_permissions.manage_emojis or not interaction.guild.me.guild_permissions.manage_emojis:
            return await interaction.response.send_message(embed=discord.Embed(
                title=f"{Emojis.HOICHAM} aree...? có lỗi gì đó ở đây",
                description="**yiyi** hoặc cậu bị thiếu gì trong máy chủ này, hãy kiểm tra lại quyền trước khi dùng lệnh nhé",
                color=0xe6e2dd
            ), ephemeral=True)

        await interaction.response.defer()
        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)

        items = await self.db_col.find({"user_id": user_id_str, "pack_name": pack_clean}).sort("stt", 1).to_list(length=None)
        if not items:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.BUOMA} gói `{pack_clean}` trống hoặc không tồn tại.", color=0xe6e2dd
            ))

        await interaction.followup.send(embed=discord.Embed(
            description=f"đang tiến hành tái bản **{len(items)}** emoji, cậu đợi xíu nhé...", color=0xe6e2dd
        ))

        success_count = 0
        async with aiohttp.ClientSession() as session:
            for item in items:
                try:
                    async with session.get(item["emoji_url"]) as resp:
                        if resp.status == 200:
                            img_bytes = await resp.read()
                            await interaction.guild.create_custom_emoji(name=item["emoji_name"], image=img_bytes)
                            success_count += 1
                            await asyncio.sleep(1.5) # Chống dính Rate Limit của Discord
                except:
                    continue

        await interaction.channel.send(embed=discord.Embed(
            title=f"{Emojis.BUOMA} tái bản hoàn tất",
            description=f"đã sao chép thành công **{success_count}/{len(items)}** emoji vào máy chủ này",
            color=0xe6e2dd
        ))

    # [6] LỆNH DELETE LẺ KÈM RE-INDEX
    @emoji.command(name="delete", description="xóa 1 emoji khỏi gói và tự động dồn hàng")
    @app_commands.describe(pack_name="tên gói", stt="số thứ tự của emoji cần xóa")
    async def emoji_delete(self, interaction: discord.Interaction, pack_name: str, stt: int):
        await interaction.response.defer(ephemeral=True)
        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)

        target = await self.db_col.find_one_and_delete({"user_id": user_id_str, "pack_name": pack_clean, "stt": stt})
        if not target:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.HOICHAM} không tìm thấy emoji số {stt}.", color=0xe6e2dd
            ))

        # Mạch Re-indexing: Vá lỗ hổng STT
        await self.db_col.update_many(
            {"user_id": user_id_str, "pack_name": pack_clean, "stt": {"$gt": stt}},
            {"$inc": {"stt": -1}}
        )

        await interaction.followup.send(embed=discord.Embed(
            description=f"{Emojis.BUOMA} đã xóa emoji số `{stt}` và dồn lại mạch danh sách.", color=0xe6e2dd
        ))

    # [7] LỆNH XÓA CẢ GÓI
    @emoji.command(name="clear", description="xóa sổ hoàn toàn một gói emoji")
    @app_commands.describe(pack_name="tên gói")
    async def emoji_clear(self, interaction: discord.Interaction, pack_name: str):
        await interaction.response.defer(ephemeral=True)
        pack_clean = pack_name.strip().lower()
        user_id_str = str(interaction.user.id)

        result = await self.db_col.delete_many({"user_id": user_id_str, "pack_name": pack_clean})
        if result.deleted_count == 0:
            return await interaction.followup.send(embed=discord.Embed(
                description=f"{Emojis.HOICHAM} không tìm thấy gói {pack_clean} để xoá.", color=0xe6e2dd
            ))

        await interaction.followup.send(embed=discord.Embed(
            description=f"{Emojis.BUOMA} đã xóa sổ gói `{pack_clean}` (dọn sạch {result.deleted_count} emoji).", color=0xe6e2dd
        ))

async def setup(bot: commands.Bot):
    # 1. Nạp đại lý Cog để Discord tự động kết nối ngữ cảnh 'self' cho các hàm xử lý DB bên trên
    cog = EmojiSync(bot)
    await bot.add_cog(cog)
    
    # 2. Thực hiện mạch chuyển hướng hạ tầng: Rút khỏi cổng toàn cục và cấy vào cổng bảo mật tổng /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Triệt tiêu cụm lệnh độc lập /emoji ngoài rìa (giấu khỏi tầm mắt mem thường)
        bot.tree.remove_command("emoji")
        
        # Khử trùng lặp nhánh con phòng hờ trường hợp hot-reload
        existing = next((cmd for cmd in p_cmd.commands if cmd.name == "emoji"), None)
        if existing:
            p_cmd.remove_command("emoji")
            
        # Tiêm nhánh lệnh vào tháp bảo vệ tổng -> trở thành /p emoji [lệnh_con]
        p_cmd.add_command(cog.emoji)
        print("[LOAD] Success: commands.emoji.emoji_sync (Connected to /p Master Shield)", flush=True)
    else:
        print("[LOAD] Warning: Không tìm thấy Master Group /p, cụm emoji tạm thời chạy ở cổng global", flush=True)
