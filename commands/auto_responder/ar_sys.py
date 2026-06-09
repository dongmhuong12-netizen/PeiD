import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
from typing import Optional

from utils.emojis import Emojis
from core.variable_engine import apply_variables

# ==========================================
# AUTOCOMPLETE MẠCH ĐỘNG (DÒ TÌM SIÊU TỐC)
# ==========================================
async def ar_text_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("AutoResponder")
    if not cog or not interaction.guild_id: return []
    try:
        cursor = cog.db_texts.find({"guild_id": interaction.guild_id})
        choices = []
        async for doc in cursor:
            name = doc.get("name")
            if name and current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
            if len(choices) >= 25: break
        return choices
    except:
        return []

async def ar_embed_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("AutoResponder")
    if not cog or not interaction.guild_id: return []
    try:
        cursor = cog.db_embeds.find({"guild_id": interaction.guild_id})
        choices = []
        async for doc in cursor:
            name = doc.get("name")
            if name and current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
            if len(choices) >= 25: break
        return choices
    except:
        return []

async def ar_trigger_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("AutoResponder")
    if not cog or not interaction.guild_id: return []
    try:
        # Bắt thẳng từ RAM Cache với tốc độ O(1)
        guild_cache = cog.cache.get(interaction.guild_id, {})
        choices = []
        for trigger in guild_cache.keys():
            if current.lower() in trigger.lower():
                choices.append(app_commands.Choice(name=trigger, value=trigger))
            if len(choices) >= 25: break
        return choices
    except:
        return []

# ==========================================
# GIAO DIỆN MODAL: CHỈNH SỬA VĂN BẢN & TỪ KHÓA
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


class TriggerEditModal(discord.ui.Modal, title='꒰ა chỉnh sửa từ khóa ໒꒱'):
    trigger_input = discord.ui.TextInput(
        label='Từ khóa mới',
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    def __init__(self, cog, old_trigger: str):
        super().__init__()
        self.cog = cog
        self.old_trigger = old_trigger
        self.trigger_input.default = old_trigger

    async def on_submit(self, interaction: discord.Interaction):
        new_trigger = self.trigger_input.value.strip().lower()
        
        if new_trigger == self.old_trigger:
            return await interaction.response.send_message(f"{Emojis.BUOMA} cậu chưa thay đổi gì cả, từ khóa vẫn được giữ nguyên nhe.", ephemeral=True)

        try:
            # Kiểm tra trùng lặp để bảo vệ mạch liên kết
            existing = await self.cog.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": new_trigger})
            if existing:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} từ khóa đã tồn tại",
                    description=f"từ khóa `{new_trigger}` đã có trong kho rồi, cậu hãy chọn tên khác hoặc dùng lệnh setup để nối thêm nhé.",
                    color=0xe6e2dd
                )
                return await interaction.response.send_message(embed=embed_err, ephemeral=True)

            # Cập nhật Database
            await self.cog.db_triggers.update_one(
                {"guild_id": interaction.guild_id, "trigger": self.old_trigger},
                {"$set": {"trigger": new_trigger}}
            )

            # Cập nhật nóng vào RAM Cache
            guild_cache = self.cog.cache.get(interaction.guild_id, {})
            if self.old_trigger in guild_cache:
                responses = guild_cache.pop(self.old_trigger)
                guild_cache[new_trigger] = responses

            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã cập nhật từ khóa",
                description=f"từ khóa `{self.old_trigger}` đã được đổi tên thành `{new_trigger}` thành công.",
                color=0xe6e2dd
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"{Emojis.HOICHAM} lỗi ghi dữ liệu: `{str(e)}`", ephemeral=True)

# ==========================================
# [NÂNG CẤP INDUSTRIAL] CỖ MÁY PHÂN TRANG AR
# ==========================================
class ArPageJumpModal(discord.ui.Modal, title="Tìm kiếm trang danh sách"):
    def __init__(self, view):
        super().__init__()
        self.view_ref = view
        self.page_input = discord.ui.TextInput(
            label="Nhập số trang cậu muốn đến",
            placeholder=f"Danh sách hiện có từ 1 đến {self.view_ref.total_pages} trang",
            required=True,
            max_length=4,
            style=discord.TextStyle.short
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.page_input.value.strip()
        if not val.isdigit():
            return await interaction.response.send_message(f"{Emojis.BUOMA} hông được rồi, cậu phải nhập số nguyên cơ, thử lại nhé.", ephemeral=True)
        
        target = int(val)
        if target < 1 or target > self.view_ref.total_pages:
            return await interaction.response.send_message(f"{Emojis.BUOMA} không có trang {target} đâu, danh sách hiện chỉ có từ 1 đến {self.view_ref.total_pages} trang thôi cậu.", ephemeral=True)
        
        self.view_ref.current_page = target - 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.build_embed(), view=self.view_ref)

class ArListPagination(discord.ui.View):
    def __init__(self, chunks, total_pages):
        super().__init__(timeout=120)
        self.chunks = chunks
        self.total_pages = total_pages
        self.current_page = 0
        self.update_buttons()
        self.message = None

    def update_buttons(self):
        self.btn_prev.disabled = self.current_page == 0
        self.btn_next.disabled = self.current_page == self.total_pages - 1

    def build_embed(self):
        embed = discord.Embed(
            title="꒰ა bảng điều khiển auto-responder ໒꒱",
            description="danh sách các biến số nhận diện đang hoạt động:",
            color=0xe6e2dd
        )
        page_items = self.chunks[self.current_page] if self.current_page < len(self.chunks) else []
        for item in page_items:
            embed.add_field(name=item["name"], value=item["value"], inline=False)
        
        embed.set_footer(text=f"Hệ thống quản lý Auto-Responder của yiyi • Trang {self.current_page + 1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="Trang trước", style=discord.ButtonStyle.secondary, custom_id="ar_prev_page", emoji="◀️")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Chọn trang", style=discord.ButtonStyle.secondary, custom_id="ar_search_page", emoji="🔍")
    async def btn_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ArPageJumpModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Trang sau", style=discord.ButtonStyle.secondary, custom_id="ar_next_page", emoji="▶️")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==========================================
# MODULE CHÍNH: AUTO RESPONDER
# ==========================================
class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # [PROXY TỰ ĐỘNG] Khai thác sức mạnh từ __getattr__ của core/mongodb.py
        self.db_texts = bot.db.ar_texts
        self.db_triggers = bot.db.ar_triggers
        self.db_embeds = bot.db.embeds

        # [LÕI RAM CACHE] Lưu trữ từ khóa trên RAM để đối chiếu tin nhắn với tốc độ ánh sáng (O(1))
        # Cấu trúc: { guild_id: { "trigger_keyword": [ {"type": "text", "name": str}, ... ] } }
        self.cache = {}
        
    async def cog_load(self):
        """[DEF] Hook khởi tạo bất đồng bộ chuẩn kiến trúc discord.py v2.0+"""
        asyncio.create_task(self.build_ram_cache())

    async def build_ram_cache(self):
        """[DEF] Tải toàn bộ cấu trúc từ khóa từ MongoDB lên RAM để tối ưu tốc độ đọc"""
        try:
            cursor = self.db_triggers.find({})
            async for doc in cursor:
                g_id = doc.get("guild_id")
                trigger = doc.get("trigger")
                responses = doc.get("responses", [])
                
                # Tự động đồng bộ/nâng cấp dữ liệu cũ (Backward Compatibility)
                if not responses:
                    if doc.get("text_name"):
                        responses.append({"type": "text", "name": doc.get("text_name")})
                    elif doc.get("embed_name"):
                        responses.append({"type": "embed", "name": doc.get("embed_name")})

                if not g_id or not trigger or not responses:
                    continue
                    
                if g_id not in self.cache:
                    self.cache[g_id] = {}
                
                self.cache[g_id][trigger] = responses
            print("[AUTO-RESPONDER] Cache RAM đã đồng bộ xé gió thành công!", flush=True)
        except Exception as e:
            print(f"[AR CACHE ERROR] Lỗi nạp bộ nhớ đệm: {e}", flush=True)

    def update_cache(self, guild_id: int, trigger: str, responses: list = None):
        """Hàm đồng bộ RAM nóng khi có thao tác Create/Update/Delete"""
        if guild_id not in self.cache:
            self.cache[guild_id] = {}
        
        if not responses:
            # Lệnh Xóa (Remove)
            self.cache[guild_id].pop(trigger, None)
        else:
            # Lệnh Setup (Upsert - Lưu mảng giá trị)
            self.cache[guild_id][trigger] = responses

    # ==========================================
    # CỖ MÁY LẮNG NGHE TOÀN CỤC (GLOBAL RADAR)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # ====================================================
        # [MÀNG LỌC BẢO VỆ KHÔNG GIAN QA]
        # Xóa mù cỗ máy AR nếu tin nhắn rơi vào Lãnh địa của QA
        # ====================================================
        qa_cog = self.bot.get_cog("QASystem")
        if qa_cog:
            qa_cfg = qa_cog.config_cache.get(message.guild.id, {})
            if message.channel.id in qa_cfg.get("channels", []):
                return
        # ====================================================

        content = message.content.strip().lower()
        if not content:
            return

        guild_id = message.guild.id

        if guild_id in self.cache and content in self.cache[guild_id]:
            responses = self.cache[guild_id][content]
            if not responses:
                return

            # CƠ CHẾ GACHA: Chọn ngẫu nhiên 1 giá trị duy nhất
            choice = random.choice(responses)

            try:
                # NHÁNH 1: GỬI VĂN BẢN
                if choice["type"] == "text":
                    doc = await self.db_texts.find_one({"guild_id": guild_id, "name": choice["name"]})
                    if doc:
                        processed_text = apply_variables(doc["content"], message.guild, message.author)
                        await message.channel.send(content=processed_text)
                
                # NHÁNH 2: GỬI EMBED
                elif choice["type"] == "embed":
                    doc = await self.db_embeds.find_one({"guild_id": guild_id, "name": choice["name"]})
                    if doc:
                        embed_data = doc.get("embed", doc) 
                        try:
                            embed = discord.Embed.from_dict(embed_data)
                            if "color" in embed_data and isinstance(embed_data["color"], str):
                                embed.color = int(embed_data["color"].replace("#", ""), 16)
                            elif "color" not in embed_data:
                                embed.color = 0xe6e2dd 
                        except Exception:
                            embed = discord.Embed(title=doc.get("name", "Embed"), description="Dữ liệu embed bị hỏng", color=0xe6e2dd)
                        
                        await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[AR RADAR ERROR] Không thể bắn phản hồi cho '{content}': {e}", flush=True)

    # ==========================================
    # HỆ THỐNG LỆNH QUẢN TRỊ SLASH COMMANDS (/ar)
    # ==========================================
    
    # [THAY ĐỔI: Gỡ khóa quyền cứng để nhường chỗ cho khóa tổng của /p]
    ar_group = app_commands.Group(name="ar", description="Hệ thống Auto-Responder phản hồi tự động")

    @ar_group.command(name="create", description="Tạo một văn bản gốc để lưu vào kho")
    @app_commands.describe(name="Tên của văn bản (dùng để liên kết sau này)", content="Nội dung văn bản (hỗ trợ đầy đủ bộ biến số)")
    async def ar_create(self, interaction: discord.Interaction, name: str, content: str):
        await interaction.response.defer(ephemeral=True)
        try:
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

    @ar_group.command(name="edit", description="Chỉnh sửa nội dung văn bản hoặc đổi tên từ khóa (Mở Modal)")
    @app_commands.describe(text_name="Tên của văn bản cần chỉnh sửa", trigger_name="Từ khóa nhận diện cần đổi tên")
    @app_commands.autocomplete(text_name=ar_text_autocomplete, trigger_name=ar_trigger_autocomplete)
    async def ar_edit(self, interaction: discord.Interaction, text_name: Optional[str] = None, trigger_name: Optional[str] = None):
        # Bộ lọc chống xung đột thao tác
        if text_name and trigger_name:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} quá nhiều lựa chọn",
                description="cậu chỉ được phép chọn sửa **Văn bản** HOẶC sửa **Từ khóa** trong cùng 1 lần thôi nhe.",
                color=0xe6e2dd
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        if not text_name and not trigger_name:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} thiếu mảnh ghép",
                description="cậu phải chọn một `text_name` hoặc một `trigger_name` để chỉnh sửa chứ.",
                color=0xe6e2dd
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # NHÁNH 1: MỞ FORM SỬA VĂN BẢN
            if text_name:
                doc = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name})
                if not doc:
                    embed_err = discord.Embed(
                        title=f"{Emojis.HOICHAM} không tìm thấy dữ liệu",
                        description=f"văn bản `{text_name}` không tồn tại trong kho.",
                        color=0xe6e2dd
                    )
                    return await interaction.response.send_message(embed=embed_err, ephemeral=True)
                
                modal = TextEditModal(cog=self, text_name=text_name, current_content=doc.get("content", ""))
                return await interaction.response.send_modal(modal)

            # NHÁNH 2: MỞ FORM SỬA TỪ KHÓA
            if trigger_name:
                trig_clean = trigger_name.strip().lower()
                doc = await self.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": trig_clean})
                if not doc:
                    embed_err = discord.Embed(
                        title=f"{Emojis.HOICHAM} không tìm thấy dữ liệu",
                        description=f"từ khóa `{trig_clean}` không tồn tại trong hệ thống.",
                        color=0xe6e2dd
                    )
                    return await interaction.response.send_message(embed=embed_err, ephemeral=True)

                modal = TriggerEditModal(cog=self, old_trigger=trig_clean)
                return await interaction.response.send_modal(modal)

        except Exception as e:
            await interaction.response.send_message(f"{Emojis.HOICHAM} lỗi truy xuất dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="delete", description="Xóa vĩnh viễn văn bản và dọn dẹp các biến số liên kết")
    @app_commands.describe(name="Tên của văn bản cần xóa")
    @app_commands.autocomplete(name=ar_text_autocomplete)
    async def ar_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.db_texts.delete_one({"guild_id": interaction.guild_id, "name": name})
            if result.deleted_count == 0:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy văn bản `{name}` để xóa.", ephemeral=True)

            deleted_triggers = []
            cursor = self.db_triggers.find({"guild_id": interaction.guild_id, "responses": {"$elemMatch": {"type": "text", "name": name}}})
            
            async for t_doc in cursor:
                trigger = t_doc.get("trigger")
                responses = t_doc.get("responses", [])
                
                new_responses = [r for r in responses if not (r["type"] == "text" and r["name"] == name)]
                
                if not new_responses:
                    await self.db_triggers.delete_one({"_id": t_doc["_id"]})
                    self.update_cache(interaction.guild_id, trigger, None)
                else:
                    await self.db_triggers.update_one({"_id": t_doc["_id"]}, {"$set": {"responses": new_responses}})
                    self.update_cache(interaction.guild_id, trigger, new_responses)
                
                if trigger:
                    deleted_triggers.append(trigger)

            trigger_log = f"\n*(đã tự động gỡ liên kết ở {len(deleted_triggers)} biến số)*" if deleted_triggers else ""
            
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã xóa văn bản",
                description=f"văn bản `{name}` đã bị xóa vĩnh viễn khỏi kho dữ liệu.{trigger_log}",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi thao tác dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="setup", description="Tạo liên kết từ khóa (Hỗ trợ cấu hình hàng loạt bằng dấu phẩy)")
    @app_commands.describe(trigger="Nhập từ khóa (Dùng dấu phẩy ',' để nhập nhiều từ khóa)", text_name="Tên văn bản muốn gắn", embed_name="Tên embed muốn gắn")
    @app_commands.autocomplete(text_name=ar_text_autocomplete, embed_name=ar_embed_autocomplete)
    async def ar_setup(self, interaction: discord.Interaction, trigger: str, text_name: Optional[str] = None, embed_name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        if text_name and embed_name:
            embed = discord.Embed(
                title=f"{Emojis.HOICHAM} xung đột logic liên kết",
                description="cậu chỉ được phép liên kết 1 **Văn bản** HOẶC 1 **Embed** trong cùng 1 lần setup nhe.",
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
            # 1. TRUY XUẤT DATABASE: Đảm bảo văn bản/embed có tồn tại
            new_entry = None
            if text_name:
                check_text = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name})
                if not check_text:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy văn bản `{text_name}` trong kho.", ephemeral=True)
                new_entry = {"type": "text", "name": text_name}
            
            if embed_name:
                check_embed = await self.db_embeds.find_one({"guild_id": interaction.guild_id, "name": embed_name})
                if not check_embed:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy embed `{embed_name}` trong kho.", ephemeral=True)
                new_entry = {"type": "embed", "name": embed_name}

            # 2. XỬ LÝ HÀNG LOẠT: Phân tách mảng từ khóa bằng dấu phẩy
            triggers_list = [t.strip().lower() for t in trigger.split(",") if t.strip()]
            success_count = 0
            skipped_count = 0

            for trig in triggers_list:
                trigger_doc = await self.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": trig})
                responses = []
                if trigger_doc:
                    responses = trigger_doc.get("responses", [])
                    if not responses:
                        if trigger_doc.get("text_name"): responses.append({"type": "text", "name": trigger_doc["text_name"]})
                        elif trigger_doc.get("embed_name"): responses.append({"type": "embed", "name": trigger_doc["embed_name"]})

                # Chống nhồi trùng lặp cùng 1 loại
                if new_entry in responses:
                    skipped_count += 1
                    continue

                responses.append(new_entry)

                await self.db_triggers.update_one(
                    {"guild_id": interaction.guild_id, "trigger": trig},
                    {"$set": {"responses": responses}, "$unset": {"text_name": "", "embed_name": ""}},
                    upsert=True
                )
                
                # Cập nhật Cache RAM
                self.update_cache(interaction.guild_id, trig, responses)
                success_count += 1

            # BÁO CÁO CÔNG SỨC
            target_str = f"văn bản `{text_name}`" if text_name else f"embed `{embed_name}`"
            trigger_view = f"`{triggers_list[0]}`" + (f" và {len(triggers_list)-1} từ khóa khác" if len(triggers_list) > 1 else "")
            
            desc = f"từ khóa {trigger_view} đã được móc nối với {target_str}.\n"
            if skipped_count > 0:
                desc += f"\n*(bỏ qua {skipped_count} liên kết do đã tồn tại từ trước)*"

            embed = discord.Embed(
                title=f"{Emojis.BUOMA} khởi tạo mạch liên kết hoàn tất",
                description=desc,
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi đồng bộ mạch liên kết: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="remove", description="Gỡ bỏ hoàn toàn liên kết từ khóa (Hỗ trợ nhiều từ khóa bằng dấu phẩy)")
    @app_commands.describe(trigger="Từ khóa muốn gỡ (Dùng dấu phẩy ',' để gỡ nhiều)")
    @app_commands.autocomplete(trigger=ar_trigger_autocomplete)
    async def ar_remove(self, interaction: discord.Interaction, trigger: str):
        await interaction.response.defer(ephemeral=True)
        
        triggers_list = [t.strip().lower() for t in trigger.split(",") if t.strip()]
        success_list = []

        try:
            for trig in triggers_list:
                result = await self.db_triggers.delete_one({"guild_id": interaction.guild_id, "trigger": trig})
                if result.deleted_count > 0:
                    self.update_cache(interaction.guild_id, trig, None)
                    success_list.append(trig)

            if not success_list:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy từ khóa nào hoạt động trong danh sách cậu nhập.", ephemeral=True)

            log_view = f"`{success_list[0]}`" + (f" và {len(success_list)-1} từ khóa khác" if len(success_list) > 1 else "")
            
            embed = discord.Embed(
                title=f"{Emojis.BUOMA} đã gỡ liên kết thành công",
                description=f"mạch nối của {log_view} đã bị chặt đứt hoàn toàn.\n*(các văn bản và embed trong kho vẫn được giữ nguyên vẹn)*",
                color=0xe6e2dd
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi thao tác dữ liệu: `{str(e)}`", ephemeral=True)

    @ar_group.command(name="list", description="Bảng điều khiển kiểm soát toàn bộ biến số")
    @app_commands.describe(trigger="Nhập tên biến số để xem chi tiết (Tùy chọn)")
    @app_commands.autocomplete(trigger=ar_trigger_autocomplete)
    async def ar_list(self, interaction: discord.Interaction, trigger: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_cache = self.cache.get(interaction.guild_id, {})
            
            if not guild_cache:
                return await interaction.followup.send(f"{Emojis.HOICHAM} chưa có từ khóa nào được thiết lập ở server này.", ephemeral=True)

            if trigger:
                trigger_lower = trigger.strip().lower()
                if trigger_lower not in guild_cache:
                    return await interaction.followup.send(f"{Emojis.HOICHAM} từ khóa `{trigger_lower}` không tồn tại trong hệ thống.", ephemeral=True)
                
                responses = guild_cache[trigger_lower]
                
                desc = "đang móc nối với các giá trị (chọn ngẫu nhiên):\n\n"
                for i, r in enumerate(responses, 1):
                    type_str = "Văn bản" if r["type"] == "text" else "Embed"
                    desc += f"**{i}.** {type_str}: `{r['name']}`\n"

                embed = discord.Embed(
                    title=f"꒰ა chi tiết từ khóa: {trigger_lower} ໒꒱",
                    description=desc,
                    color=0xe6e2dd
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)

            # Quy đổi danh sách cache thành mảng cấu trúc field
            all_fields = []
            for trig, responses in guild_cache.items():
                if len(responses) == 1:
                    target = f"Văn bản: `{responses[0]['name']}`" if responses[0]["type"] == "text" else f"Embed: `{responses[0]['name']}`"
                else:
                    target = f"Liên kết với {len(responses)} giá trị (Random)"
                all_fields.append({"name": f"Từ khóa: {trig}", "value": f"↳ {target}"})

            def chunk_list(lst, n):
                return [lst[i:i + n] for i in range(0, len(lst), n)]

            # Gom 10 từ khóa vào một trang cho thoáng và đẹp mắt
            chunks = chunk_list(all_fields, 10) or [[]]
            total_pages = len(chunks)

            if total_pages <= 1:
                embed = discord.Embed(
                    title=f"꒰ა bảng điều khiển auto-responder ໒꒱",
                    description="danh sách các biến số nhận diện đang hoạt động:",
                    color=0xe6e2dd
                )
                for item in chunks[0]:
                    embed.add_field(name=item["name"], value=item["value"], inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Kích hoạt Cỗ máy UI Phân trang nâng cao
                view = ArListPagination(chunks, total_pages)
                msg = await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)
                view.message = msg

        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi truy xuất danh sách: `{str(e)}`", ephemeral=True)

async def setup(bot: commands.Bot):
    # 1. Nạp Cog để giữ nguyên hệ mạch Database và cỗ máy Lắng nghe
    cog = AutoResponder(bot)
    await bot.add_cog(cog)
    
    # 2. Rút /ar cũ ra và ghim vào cổng tổng /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn rác
        bot.tree.remove_command("ar")
        existing = next((cmd for cmd in p_cmd.commands if cmd.name == "ar"), None)
        if existing: 
            p_cmd.remove_command("ar")
        
        # Tiêm mạch
        p_cmd.add_command(cog.ar_group)
        print("[LOAD] Success: commands.auto_responder.ar_sys (Connected to /p Master Shield)", flush=True)
    else:
        print("[LOAD] Warning: Không tìm thấy /p. Cụm AR chạy độc lập.", flush=True)
