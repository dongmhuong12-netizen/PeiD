import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import Optional

from utils.emojis import Emojis
from core.variable_engine import apply_variables

# ==========================================
# GIAO DIỆN MODAL: CHỈNH SỬA VĂN BẢN
# ==========================================
class TextEditModal(discord.ui.Modal, title='꒰ა chỉnh sửa nội dung văn bản ໒꒱'):
    content_input = discord.ui.TextInput(
        label='Nội dung (Hỗ trợ biến số)',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    def __init__(self, cog, text_name: str, current_content: str):
        super().__init__()
        self.cog = cog
        self.text_name = text_name
        # Đổ sẵn nội dung cũ vào khung cho sếp sửa
        self.content_input.default = current_content

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Cập nhật thẳng vào MongoDB
            await self.cog.db_texts.update_one(
                {"guild_id": interaction.guild_id, "name": self.text_name},
                {"$set": {"content": self.content_input.value}}
            )
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã cập nhật văn bản",
                description=f"văn bản `{self.text_name}` đã được chỉnh sửa và niêm phong thành công.",
                color=0xe6e2dd
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{Emojis.HOICHAM} lỗi ghi dữ liệu: `{str(e)}`", ephemeral=True)


# ==========================================
# MODULE CHÍNH: AUTO RESPONDER
# ==========================================
class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # [PROXY TỰ ĐỘNG] Khai thác sức mạnh từ __getattr__ của core/mongodb.py
        # Không cần sửa file mongodb, proxy sẽ tự động tạo kết nối tới các kho này
        self.db_texts = bot.db.ar_texts
        self.db_triggers = bot.db.ar_triggers
        self.db_embeds = bot.db.embeds

        # [LÕI RAM CACHE] Lưu trữ từ khóa trên RAM để đối chiếu tin nhắn với tốc độ ánh sáng (O(1))
        # Cấu trúc: { guild_id: { "trigger_keyword": {"text_name": str, "embed_name": str} } }
        self.cache = {}
        
    async def cog_load(self):
        """[DEF] Hook khởi tạo bất đồng bộ chuẩn kiến trúc discord.py v2.0+"""
        # Khởi động nạp Cache an toàn khi event loop đã sẵn sàng
        asyncio.create_task(self.build_ram_cache())

    async def build_ram_cache(self):
        """[DEF] Tải toàn bộ cấu trúc từ khóa từ MongoDB lên RAM để tối ưu tốc độ đọc"""
        try:
            cursor = self.db_triggers.find({})
            async for doc in cursor:
                g_id = doc.get("guild_id")
                trigger = doc.get("trigger")
                if not g_id or not trigger:
                    continue
                    
                if g_id not in self.cache:
                    self.cache[g_id] = {}
                
                self.cache[g_id][trigger] = {
                    "text_name": doc.get("text_name"),
                    "embed_name": doc.get("embed_name")
                }
            print("[AUTO-RESPONDER] Cache RAM đã đồng bộ xé gió thành công!", flush=True)
        except Exception as e:
            print(f"[AR CACHE ERROR] Lỗi nạp bộ nhớ đệm: {e}", flush=True)

    def update_cache(self, guild_id: int, trigger: str, text_name: str = None, embed_name: str = None):
        """Hàm đồng bộ RAM nóng khi có thao tác Create/Update/Delete"""
        if guild_id not in self.cache:
            self.cache[guild_id] = {}
        
        if text_name is None and embed_name is None:
            # Lệnh Xóa (Remove)
            self.cache[guild_id].pop(trigger, None)
        else:
            # Lệnh Setup (Upsert)
            self.cache[guild_id][trigger] = {
                "text_name": text_name,
                "embed_name": embed_name
            }

    # ==========================================
    # CỖ MÁY LẮNG NGHE TOÀN CỤC (GLOBAL RADAR)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # [DEF] Bỏ qua bot và tin nhắn DM để tránh kẹt hệ thống
        if message.author.bot or not message.guild:
            return

        # Vệ sinh tin nhắn và chuyển chữ thường để khớp chính xác
        content = message.content.strip().lower()
        if not content:
            return

        guild_id = message.guild.id

        # [ATK] Kích hoạt Radar quét RAM. Tốc độ thực thi: O(1)
        if guild_id in self.cache and content in self.cache[guild_id]:
            config = self.cache[guild_id][content]
            text_name = config.get("text_name")
            embed_name = config.get("embed_name")

            try:
                # NHÁNH 1: GỬI VĂN BẢN (Biên dịch qua Variable Engine)
                if text_name:
                    doc = await self.db_texts.find_one({"guild_id": guild_id, "name": text_name})
                    if doc:
                        processed_text = apply_variables(doc["content"], message.guild, message.author)
                        await message.channel.send(content=processed_text)
                
                # NHÁNH 2: GỬI EMBED CŨ
                elif embed_name:
                    doc = await self.db_embeds.find_one({"guild_id": guild_id, "name": embed_name})
                    if doc:
                        # Hỗ trợ tự động bóc tách bộ xương Embed từ DB
                        embed_data = doc.get("embed", doc) 
                        
                        try:
                            embed = discord.Embed.from_dict(embed_data)
                            # Kiểm tra nếu DB lưu Color dưới dạng int hoặc hex string
                            if "color" in embed_data and isinstance(embed_data["color"], str):
                                embed.color = int(embed_data["color"].replace("#", ""), 16)
                            elif "color" not in embed_data:
                                embed.color = 0xe6e2dd # Màu mặc định của sếp
                        except Exception:
                            # Khôi phục an toàn nếu cấu trúc lệch
                            embed = discord.Embed(title=doc.get("name", "Embed"), description="Dữ liệu embed bị hỏng", color=0xe6e2dd)
                        
                        await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[AR RADAR ERROR] Không thể bắn phản hồi cho '{content}': {e}", flush=True)

        # Lưu ý Architect: Sử dụng @commands.Cog.listener() thì KHÔNG cần process_commands(message) 
        # Sự kiện ngầm này sẽ tự động chạy song song, tuyệt đối không "nuốt" các lệnh text như !sy

    # ==========================================
    # HỆ THỐNG LỆNH QUẢN TRỊ SLASH COMMANDS (/ar)
    # ==========================================
    ar_group = app_commands.Group(name="ar", description="Hệ thống Auto-Responder phản hồi tự động", default_permissions=discord.Permissions(manage_guild=True))

    @ar_group.command(name="create", description="Tạo một văn bản gốc để lưu vào kho")
    @app_commands.describe(name="Tên của văn bản (dùng để liên kết sau này)", content="Nội dung văn bản (hỗ trợ đầy đủ bộ biến số)")
    async def ar_create(self, interaction: discord.Interaction, name: str, content: str):
        await interaction.response.defer(ephemeral=True)
        try:
            # Ghi đè hoặc tạo mới vào kho Văn bản
            await self.db_texts.update_one(
                {"guild_id": interaction.guild_id, "name": name},
                {"$set": {"content": content}},
                upsert=True
            )
            
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã lưu văn bản thành công",
                description=f"văn bản `{name}` đã được niêm phong vào kho dữ liệu.",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi ghi dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="edit", description="Chỉnh sửa nội dung văn bản qua bảng biểu mẫu (Modal)")
    @app_commands.describe(name="Tên của văn bản cần chỉnh sửa")
    async def ar_edit(self, interaction: discord.Interaction, name: str):
        # Không defer ở đây vì Modal yêu cầu phản hồi lập tức
        try:
            doc = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": name})
            if not doc:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} không tìm thấy dữ liệu",
                    description=f"văn bản `{name}` không tồn tại trong kho.",
                    color=0xe6e2dd
                )
                return await interaction.response.send_message(embed=embed_err, ephemeral=True)
            
            # Khởi tạo Modal và đẩy nội dung cũ vào
            modal = TextEditModal(cog=self, text_name=name, current_content=doc.get("content", ""))
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(f"{Emojis.HOICHAM} lỗi truy xuất dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="delete", description="Xóa vĩnh viễn văn bản và dọn dẹp các biến số liên kết")
    @app_commands.describe(name="Tên của văn bản cần xóa")
    async def ar_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            # 1. Tiêu diệt Văn Bản gốc
            result = await self.db_texts.delete_one({"guild_id": interaction.guild_id, "name": name})
            if result.deleted_count == 0:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy văn bản `{name}` để xóa.", ephemeral=True)

            # 2. Thuật toán dọn dẹp: Cắt đứt và quét sạch toàn bộ Trigger đang bám vào văn bản này
            deleted_triggers = []
            cursor = self.db_triggers.find({"guild_id": interaction.guild_id, "text_name": name})
            async for t_doc in cursor:
                trigger = t_doc.get("trigger")
                if trigger:
                    deleted_triggers.append(trigger)
                    # Xóa khỏi RAM ngay lập tức
                    self.update_cache(interaction.guild_id, trigger, text_name=None, embed_name=None)
            
            # Xóa hàng loạt trên Database
            if deleted_triggers:
                await self.db_triggers.delete_many({"guild_id": interaction.guild_id, "text_name": name})

            trigger_log = f"\n*(đã tự động dọn dẹp {len(deleted_triggers)} biến số liên kết)*" if deleted_triggers else ""
            
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã xóa văn bản",
                description=f"văn bản `{name}` đã bị xóa vĩnh viễn khỏi kho dữ liệu.{trigger_log}",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi thao tác dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="setup", description="Tạo liên kết từ khóa tới Văn bản hoặc Embed")
    @app_commands.describe(trigger="Từ khóa kích hoạt (VD: welcome)", text_name="Tên văn bản muốn gắn", embed_name="Tên embed muốn gắn")
    async def ar_setup(self, interaction: discord.Interaction, trigger: str, text_name: Optional[str] = None, embed_name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        trigger_lower = trigger.strip().lower()

        # [LOGIC GATE] Kiểm tra Độc lập & Xung đột
        if text_name and embed_name:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} xung đột logic liên kết",
                description="cậu chỉ được phép liên kết từ khóa với **Văn bản** HOẶC **Embed**.\n\nkhông được nhồi cả hai cùng lúc để bảo vệ mạch dữ liệu độc lập của hệ thống cũ nha.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        if not text_name and not embed_name:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} thiếu mảnh ghép",
                description="cậu phải cung cấp ít nhất một `text_name` hoặc một `embed_name` để tạo liên kết.",
                color=0xe6e2dd
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        try:
            # [DEF] Kiểm tra sự tồn tại của dữ liệu trước khi móc nối
            if text_name:
                check_text = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name})
                if not check_text:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy văn bản `{text_name}` trong kho. cậu tạo lệnh `/ar create` trước nhé.", ephemeral=True)
            
            if embed_name:
                check_embed = await self.db_embeds.find_one({"guild_id": interaction.guild_id, "name": embed_name})
                if not check_embed:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{embed_name}` trong kho của hệ thống cũ.", ephemeral=True)

            # Lưu vào Database Từ Khóa
            await self.db_triggers.update_one(
                {"guild_id": interaction.guild_id, "trigger": trigger_lower},
                {"$set": {"text_name": text_name, "embed_name": embed_name}},
                upsert=True
            )
            
            # Đồng bộ Cache RAM nóng
            self.update_cache(interaction.guild_id, trigger_lower, text_name, embed_name)

            target_str = f"văn bản `{text_name}`" if text_name else f"embed `{embed_name}`"
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} khởi tạo mạch liên kết hoàn tất",
                description=f"từ khóa **{trigger_lower}** đã được móc nối thành công với {target_str}.\nhệ thống radar đã được kích hoạt.",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi đồng bộ mạch liên kết: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="remove", description="Gỡ bỏ hoàn toàn một liên kết từ khóa")
    @app_commands.describe(trigger="Từ khóa muốn gỡ (VD: welcome)")
    async def ar_remove(self, interaction: discord.Interaction, trigger: str):
        await interaction.response.defer(ephemeral=True)
        trigger_lower = trigger.strip().lower()

        try:
            result = await self.db_triggers.delete_one({"guild_id": interaction.guild_id, "trigger": trigger_lower})
            
            if result.deleted_count == 0:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy từ khóa `{trigger_lower}` nào đang hoạt động cả.", ephemeral=True)

            # Xóa khỏi Cache RAM
            self.update_cache(interaction.guild_id, trigger_lower, text_name=None, embed_name=None)

            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã gỡ liên kết",
                description=f"mạch nối của từ khóa **{trigger_lower}** đã bị chặt đứt.\n*(văn bản và embed trong kho vẫn được giữ nguyên vẹn)*",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi thao tác dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="list", description="Bảng điều khiển kiểm soát toàn bộ biến số")
    @app_commands.describe(trigger="Nhập tên biến số để xem chi tiết (Tùy chọn)")
    async def ar_list(self, interaction: discord.Interaction, trigger: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Kéo data từ RAM siêu tốc thay vì gọi DB
            guild_cache = self.cache.get(interaction.guild_id, {})
            
            if not guild_cache:
                return await interaction.followup.send(f"{Emojis.HOICHAM} chưa có từ khóa nào được thiết lập ở server này.", ephemeral=True)

            # NHÁNH 1: TÌM KIẾM CHI TIẾT TỪ KHÓA
            if trigger:
                trigger_lower = trigger.strip().lower()
                if trigger_lower not in guild_cache:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} từ khóa `{trigger_lower}` không tồn tại trong hệ thống.", ephemeral=True)
                
                config = guild_cache[trigger_lower]
                
                if config.get("embed_name"):
                    embed = discord.Embed(
                        title=f"꒰ა chi tiết từ khóa: {trigger_lower} ໒꒱",
                        description=f"đang móc nối với embed: `{config['embed_name']}`",
                        color=0xe6e2dd
                    )
                    return await interaction.followup.send(embed=embed, ephemeral=True)
                
                if config.get("text_name"):
                    text_name = config["text_name"]
                    doc = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name})
                    
                    if doc:
                        embed = discord.Embed(
                            title=f"꒰ა chi tiết từ khóa: {trigger_lower} ໒꒱",
                            description=f"đang móc nối với văn bản: `{text_name}`\n\n**nội dung nguyên bản:**\n```text\n{doc['content']}\n```",
                            color=0xe6e2dd
                        )
                    else:
                        embed = discord.Embed(
                            title=f"꒰ა chi tiết từ khóa: {trigger_lower} ໒꒱",
                            description=f"đang móc nối với văn bản: `{text_name}`\n\n{Emojis.HOICHAM} *(lỗi: không thể trích xuất nội dung từ kho)*",
                            color=0xe6e2dd
                        )
                    return await interaction.followup.send(embed=embed, ephemeral=True)

            # NHÁNH 2: BẢNG DANH SÁCH TỔNG QUAN
            embed = discord.Embed(
                title=f"꒰ა bảng điều khiển auto-responder ໒꒱",
                description="danh sách các biến số nhận diện đang hoạt động:",
                color=0xe6e2dd
            )

            count = 0
            for trig, config in guild_cache.items():
                target = f"Văn bản: `{config['text_name']}`" if config.get("text_name") else f"Embed: `{config['embed_name']}`"
                # Đóng gói giới hạn hiển thị (Discord cho tối đa 25 field)
                if count < 25:
                    embed.add_field(name=f"Từ khóa: {trig}", value=f"↳ Trỏ tới {target}", inline=False)
                    count += 1
                else:
                    embed.set_footer(text=f"và {len(guild_cache) - 25} từ khóa khác... (đang ẩn)")
                    break

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi truy xuất danh sách: `{str(e)}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoResponder(bot))
    print("[LOAD] Success: commands.auto_responder.ar_sys (Full Engine: Modal Edit & Deep Clean Delete Injected)", flush=True)
