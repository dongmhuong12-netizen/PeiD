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
async def qa_text_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("QASystem")
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

async def qa_embed_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("QASystem")
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

async def qa_trigger_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("QASystem")
    if not cog or not interaction.guild_id: return []
    try:
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
# GIAO DIỆN MODAL: CHỈNH SỬA
# ==========================================
class QaTextEditModal(discord.ui.Modal, title='꒰ა chỉnh sửa nội dung văn bản ໒꒱'):
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
        self.content_input.default = current_content

    async def on_submit(self, interaction: discord.Interaction):
        try:
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


class QaTriggerEditModal(discord.ui.Modal, title='꒰ა chỉnh sửa từ khóa ໒꒱'):
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
            existing = await self.cog.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": new_trigger})
            if existing:
                embed_err = discord.Embed(
                    title=f"{Emojis.HOICHAM} từ khóa đã tồn tại",
                    description=f"từ khóa `{new_trigger}` đã có trong kho rồi.",
                    color=0xe6e2dd
                )
                return await interaction.response.send_message(embed=embed_err, ephemeral=True)

            await self.cog.db_triggers.update_one(
                {"guild_id": interaction.guild_id, "trigger": self.old_trigger},
                {"$set": {"trigger": new_trigger}}
            )

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
# CỖ MÁY PHÂN TRANG DANH SÁCH QA
# ==========================================
class QaPageJumpModal(discord.ui.Modal, title="Tìm kiếm trang danh sách"):
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
            return await interaction.response.send_message(f"{Emojis.BUOMA} cậu phải nhập số nguyên cơ.", ephemeral=True)
        
        target = int(val)
        if target < 1 or target > self.view_ref.total_pages:
            return await interaction.response.send_message(f"{Emojis.BUOMA} không có trang {target} đâu.", ephemeral=True)
        
        self.view_ref.current_page = target - 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.build_embed(), view=self.view_ref)

class QaListPagination(discord.ui.View):
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
            title="꒰ა bảng điều khiển hỏi đáp yiyi ໒꒱",
            description="danh sách các từ khóa hỏi đáp đang hoạt động:",
            color=0xe6e2dd
        )
        page_items = self.chunks[self.current_page] if self.current_page < len(self.chunks) else []
        for item in page_items:
            embed.add_field(name=item["name"], value=item["value"], inline=False)
        
        embed.set_footer(text=f"Hệ thống Hỏi Đáp Yiyi • Trang {self.current_page + 1}/{self.total_pages}")
        return embed

    @discord.ui.button(label="Trang trước", style=discord.ButtonStyle.secondary, custom_id="qa_prev_page", emoji="◀️")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Chọn trang", style=discord.ButtonStyle.secondary, custom_id="qa_search_page", emoji="🔍")
    async def btn_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = QaPageJumpModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Trang sau", style=discord.ButtonStyle.secondary, custom_id="qa_next_page", emoji="▶️")
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
# MODULE CHÍNH: HỆ THỐNG QA (LOCAL RADAR)
# ==========================================
class QASystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Isolation: Tách kho lưu trữ độc lập hoàn toàn khỏi /ar
        self.db_texts = bot.db.qa_texts
        self.db_triggers = bot.db.qa_triggers
        self.db_configs = bot.db.qa_configs
        self.db_embeds = bot.db.embeds

        self.cache = {}        # Chứa Từ khóa
        self.config_cache = {} # Chứa Cấu hình không gian (Kênh, Timer, Reminder)
        
    async def cog_load(self):
        asyncio.create_task(self.build_ram_cache())

    async def build_ram_cache(self):
        try:
            # 1. Nạp Từ khóa
            cursor_trig = self.db_triggers.find({})
            async for doc in cursor_trig:
                g_id = doc.get("guild_id")
                trigger = doc.get("trigger")
                responses = doc.get("responses", [])
                
                if not responses:
                    if doc.get("text_name"): responses.append({"type": "text", "name": doc.get("text_name")})
                    elif doc.get("embed_name"): responses.append({"type": "embed", "name": doc.get("embed_name")})

                if not g_id or not trigger or not responses: continue
                if g_id not in self.cache: self.cache[g_id] = {}
                self.cache[g_id][trigger] = responses
            
            # 2. Nạp Cấu hình Không gian
            cursor_cfg = self.db_configs.find({})
            async for doc in cursor_cfg:
                g_id = doc.get("guild_id")
                if g_id:
                    self.config_cache[g_id] = {
                        "channels": doc.get("channels", []),
                        "autodelete": doc.get("autodelete", {"status": False, "user": 5, "yiyi": 5}),
                        "reminder": doc.get("reminder", "cậu ơi, ở kênh này tớ chỉ nhận từ khóa thôi nhe.")
                    }
                    
            print("[QA-SYSTEM] Kích hoạt cỗ máy Radar Cục Bộ thành công!", flush=True)
        except Exception as e:
            print(f"[QA CACHE ERROR]: {e}", flush=True)

    def update_cache(self, guild_id: int, trigger: str, responses: list = None):
        if guild_id not in self.cache:
            self.cache[guild_id] = {}
        if not responses:
            self.cache[guild_id].pop(trigger, None)
        else:
            self.cache[guild_id][trigger] = responses

    def ensure_config(self, guild_id: int):
        if guild_id not in self.config_cache:
            self.config_cache[guild_id] = {
                "channels": [],
                "autodelete": {"status": False, "user": 5, "yiyi": 5},
                "reminder": "cậu ơi, ở kênh này tớ chỉ nhận từ khóa thôi nhe."
            }

    # ==========================================
    # CỖ MÁY LẮNG NGHE ĐỊA PHƯƠNG (LOCAL RADAR)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        g_id = message.guild.id
        config = self.config_cache.get(g_id)
        
        # Mù và Điếc nếu không nằm trong danh sách Kênh đã Gán
        if not config or message.channel.id not in config.get("channels", []):
            return

        ad = config.get("autodelete", {})
        ad_status = ad.get("status", False)
        u_timer = ad.get("user", 5)
        y_timer = ad.get("yiyi", 5)

        # Trảm tin nhắn của User (nếu bật Config)
        if ad_status:
            try:
                await message.delete(delay=u_timer)
            except:
                pass # Chống crash nếu mất quyền Manage Messages

        content = message.content.strip().lower()
        guild_cache = self.cache.get(g_id, {})

        if content and content in guild_cache and guild_cache[content]:
            # TRÚNG ĐÍCH -> Lấy ngẫu nhiên & Bắn
            choice = random.choice(guild_cache[content])
            del_delay = y_timer if ad_status else None
            try:
                if choice["type"] == "text":
                    doc = await self.db_texts.find_one({"guild_id": g_id, "name": choice["name"]})
                    if doc:
                        processed_text = apply_variables(doc["content"], message.guild, message.author)
                        await message.channel.send(content=processed_text, delete_after=del_delay)
                elif choice["type"] == "embed":
                    doc = await self.db_embeds.find_one({"guild_id": g_id, "name": choice["name"]})
                    if doc:
                        embed_data = doc.get("embed", doc) 
                        try:
                            embed = discord.Embed.from_dict(embed_data)
                            if "color" in embed_data and isinstance(embed_data["color"], str):
                                embed.color = int(embed_data["color"].replace("#", ""), 16)
                            elif "color" not in embed_data:
                                embed.color = 0xe6e2dd 
                        except:
                            embed = discord.Embed(title=doc.get("name", "Embed"), description="Dữ liệu embed bị hỏng", color=0xe6e2dd)
                        
                        await message.channel.send(embed=embed, delete_after=del_delay)
            except Exception as e:
                print(f"[QA RADAR ERROR]: {e}", flush=True)
        else:
            # TRƯỢT ĐÍCH -> Phun nhắc nhở (Lọc rác kênh chat)
            reminder_text = config.get("reminder", "cậu ơi, ở kênh này tớ chỉ nhận từ khóa thôi nhe.")
            try:
                processed_rem = apply_variables(reminder_text, message.guild, message.author)
                del_delay = y_timer if ad_status else None
                await message.channel.send(content=processed_rem, delete_after=del_delay)
            except:
                pass


    # ==========================================
    # QUẢN TRỊ HỆ THỐNG QA (/qa)
    # ==========================================
    
    # [THAY ĐỔI: Gỡ khóa quyền cứng để nhường chỗ cho khóa tổng của /p]
    qa_group = app_commands.Group(name="qa", description="Hệ thống Hỏi Đáp Yiyi Cục bộ (Local Q&A)")

    @qa_group.command(name="bind", description="Gán cỗ máy Radar Hỏi Đáp vào một kênh cụ thể")
    @app_commands.describe(channel="Kênh văn bản muốn kích hoạt")
    async def qa_bind(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        self.ensure_config(interaction.guild_id)
        
        channels = self.config_cache[interaction.guild_id]["channels"]
        if channel.id in channels:
            return await interaction.followup.send(f"{Emojis.HOICHAM} kênh {channel.mention} đã được gắn Radar từ trước rồi.", ephemeral=True)
            
        channels.append(channel.id)
        await self.db_configs.update_one(
            {"guild_id": interaction.guild_id},
            {"$set": {"channels": channels}},
            upsert=True
        )
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} đã mở rộng vùng Lắng nghe", description=f"Radar Hỏi đáp Yiyi đã được thiết lập thành công tại {channel.mention}.", color=0xe6e2dd)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @qa_group.command(name="unbind", description="Gỡ bỏ cỗ máy Radar khỏi một kênh")
    @app_commands.describe(channel="Kênh văn bản muốn gỡ bỏ")
    async def qa_unbind(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        self.ensure_config(interaction.guild_id)
        
        channels = self.config_cache[interaction.guild_id]["channels"]
        if channel.id not in channels:
            return await interaction.followup.send(f"{Emojis.HOICHAM} kênh {channel.mention} hiện không có Radar nào đang chạy.", ephemeral=True)
            
        channels.remove(channel.id)
        await self.db_configs.update_one(
            {"guild_id": interaction.guild_id},
            {"$set": {"channels": channels}},
            upsert=True
        )
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} đã thu hồi Radar", description=f"đã ngắt kết nối hệ thống Hỏi đáp tại kênh {channel.mention}.", color=0xe6e2dd)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @qa_group.command(name="autodelete", description="Cấu hình công tắc tự hủy tin nhắn cho Kênh Hỏi Đáp")
    @app_commands.describe(status="Bật hoặc Tắt", user_timer="Độ trễ xóa tin nhắn của user (giây)", yiyi_timer="Độ trễ xóa phản hồi của yiyi (giây)")
    @app_commands.choices(status=[app_commands.Choice(name="Bật", value=1), app_commands.Choice(name="Tắt", value=0)])
    async def qa_autodelete(self, interaction: discord.Interaction, status: int, user_timer: int, yiyi_timer: int):
        await interaction.response.defer(ephemeral=True)
        self.ensure_config(interaction.guild_id)
        
        autodelete_cfg = {"status": bool(status), "user": user_timer, "yiyi": yiyi_timer}
        self.config_cache[interaction.guild_id]["autodelete"] = autodelete_cfg
        
        await self.db_configs.update_one(
            {"guild_id": interaction.guild_id},
            {"$set": {"autodelete": autodelete_cfg}},
            upsert=True
        )
        
        st_text = "ĐÃ BẬT" if status else "ĐÃ TẮT"
        desc = f"Chế độ dọn dẹp không gian: **{st_text}**\n↳ Tin nhắn User bốc hơi sau: `{user_timer}s`\n↳ Phản hồi Yiyi bốc hơi sau: `{yiyi_timer}s`"
        
        embed = discord.Embed(title=f"{Emojis.BUOMA} cập nhật công tắc dọn dẹp", description=desc, color=0xe6e2dd)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @qa_group.command(name="reminder", description="Chỉnh sửa câu nhắc nhở khi User gõ sai từ khóa")
    @app_commands.describe(content="Nội dung lời nhắc nhở")
    async def qa_reminder(self, interaction: discord.Interaction, content: str):
        await interaction.response.defer(ephemeral=True)
        self.ensure_config(interaction.guild_id)
        
        self.config_cache[interaction.guild_id]["reminder"] = content
        await self.db_configs.update_one(
            {"guild_id": interaction.guild_id},
            {"$set": {"reminder": content}},
            upsert=True
        )
        embed = discord.Embed(title=f"{Emojis.BUOMA} đã cập nhật lời nhắc", description=f"khi có người chat lạc đề, cỗ máy sẽ báo: `{content}`", color=0xe6e2dd)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @qa_group.command(name="config", description="Bảng điều khiển tổng quan các cài đặt của Hệ thống QA")
    async def qa_config(self, interaction: discord.Interaction):
        self.ensure_config(interaction.guild_id)
        cfg = self.config_cache[interaction.guild_id]
        
        channels_str = ", ".join([f"<#{cid}>" for cid in cfg["channels"]]) if cfg["channels"] else "Chưa gán kênh nào"
        ad = cfg["autodelete"]
        ad_str = f"Bật (User: {ad['user']}s | Yiyi: {ad['yiyi']}s)" if ad["status"] else "Đang Tắt"
        
        embed = discord.Embed(title="꒰ა bảng điều khiển không gian hỏi đáp ໒꒱", color=0xe6e2dd)
        embed.add_field(name="📍 Kênh Radar Hoạt Động", value=channels_str, inline=False)
        embed.add_field(name="⏱️ Công Tắc Dọn Dẹp (Auto-Delete)", value=ad_str, inline=False)
        embed.add_field(name="💬 Lời Nhắc Trượt Đích", value=f"`{cfg['reminder']}`", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # CÁC LỆNH CRUD LÕI KẾ THỪA TỪ AR ĐÃ UPDATE LOGIC CHỐNG TRÙNG GACHA
    @qa_group.command(name="create", description="Tạo một văn bản Hỏi Đáp để lưu vào kho")
    @app_commands.describe(name="Tên của văn bản", content="Nội dung văn bản")
    async def qa_create(self, interaction: discord.Interaction, name: str, content: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.db_texts.update_one({"guild_id": interaction.guild_id, "name": name}, {"$set": {"content": content}}, upsert=True)
            embed = discord.Embed(title=f"{Emojis.BUOMA} đã lưu văn bản thành công", description=f"văn bản `{name}` đã được niêm phong vào kho dữ liệu Hỏi Đáp.", color=0xe6e2dd)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"{Emojis.HOICHAM} lỗi ghi dữ liệu: `{str(e)}`", ephemeral=True)

    @qa_group.command(name="edit", description="Chỉnh sửa nội dung văn bản hoặc đổi tên từ khóa")
    @app_commands.describe(text_name="Tên của văn bản cần chỉnh sửa", trigger_name="Từ khóa nhận diện cần đổi tên")
    @app_commands.autocomplete(text_name=qa_text_autocomplete, trigger_name=qa_trigger_autocomplete)
    async def qa_edit(self, interaction: discord.Interaction, text_name: Optional[str] = None, trigger_name: Optional[str] = None):
        if text_name and trigger_name:
            return await interaction.response.send_message(embed=discord.Embed(title=f"{Emojis.HOICHAM} xung đột", description="chỉ chọn 1 thứ để sửa.", color=0xe6e2dd), ephemeral=True)
        if not text_name and not trigger_name:
            return await interaction.response.send_message(embed=discord.Embed(title=f"{Emojis.HOICHAM} thiếu thông tin", description="phải chọn 1 mục để sửa.", color=0xe6e2dd), ephemeral=True)

        try:
            if text_name:
                doc = await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name})
                if not doc: return await interaction.response.send_message(f"không tìm thấy `{text_name}`.", ephemeral=True)
                return await interaction.response.send_modal(QaTextEditModal(self, text_name, doc.get("content", "")))

            if trigger_name:
                trig_clean = trigger_name.strip().lower()
                doc = await self.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": trig_clean})
                if not doc: return await interaction.response.send_message(f"không tìm thấy `{trig_clean}`.", ephemeral=True)
                return await interaction.response.send_modal(QaTriggerEditModal(self, trig_clean))
        except Exception as e:
            await interaction.response.send_message(f"lỗi: `{str(e)}`", ephemeral=True)

    @qa_group.command(name="delete", description="Xóa vĩnh viễn văn bản khỏi kho Hỏi Đáp")
    @app_commands.describe(name="Tên của văn bản cần xóa")
    @app_commands.autocomplete(name=qa_text_autocomplete)
    async def qa_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await self.db_texts.delete_one({"guild_id": interaction.guild_id, "name": name})
            if result.deleted_count == 0:
                return await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy văn bản `{name}`.", ephemeral=True)

            cursor = self.db_triggers.find({"guild_id": interaction.guild_id, "responses": {"$elemMatch": {"type": "text", "name": name}}})
            async for t_doc in cursor:
                trigger = t_doc.get("trigger")
                responses = [r for r in t_doc.get("responses", []) if not (r["type"] == "text" and r["name"] == name)]
                if not responses:
                    await self.db_triggers.delete_one({"_id": t_doc["_id"]})
                    self.update_cache(interaction.guild_id, trigger, None)
                else:
                    await self.db_triggers.update_one({"_id": t_doc["_id"]}, {"$set": {"responses": responses}})
                    self.update_cache(interaction.guild_id, trigger, responses)
            
            embed = discord.Embed(title=f"{Emojis.BUOMA} đã xóa văn bản", description=f"văn bản `{name}` đã bị xóa hoàn toàn khỏi kho Hỏi Đáp.", color=0xe6e2dd)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"lỗi: `{str(e)}`", ephemeral=True)

    @qa_group.command(name="setup", description="Tạo liên kết từ khóa (Hỗ trợ cấu hình hàng loạt, cập nhật thông minh)")
    @app_commands.describe(trigger="Nhập từ khóa (Dùng dấu phẩy ',' để nhập nhiều)", text_name="Tên văn bản muốn gắn", embed_name="Tên embed muốn gắn")
    @app_commands.autocomplete(text_name=qa_text_autocomplete, embed_name=qa_embed_autocomplete)
    async def qa_setup(self, interaction: discord.Interaction, trigger: str, text_name: Optional[str] = None, embed_name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        
        if text_name and embed_name: return await interaction.followup.send("chỉ gắn 1 loại.", ephemeral=True)
        if not text_name and not embed_name: return await interaction.followup.send("thiếu dữ kiện.", ephemeral=True)

        try:
            new_entry = None
            if text_name:
                if not await self.db_texts.find_one({"guild_id": interaction.guild_id, "name": text_name}):
                    return await interaction.followup.send(f"không tìm thấy `{text_name}`.", ephemeral=True)
                new_entry = {"type": "text", "name": text_name}
            if embed_name:
                if not await self.db_embeds.find_one({"guild_id": interaction.guild_id, "name": embed_name}):
                    return await interaction.followup.send(f"không tìm thấy `{embed_name}`.", ephemeral=True)
                new_entry = {"type": "embed", "name": embed_name}

            triggers_list = [t.strip().lower() for t in trigger.split(",") if t.strip()]
            for trig in triggers_list:
                trigger_doc = await self.db_triggers.find_one({"guild_id": interaction.guild_id, "trigger": trig})
                responses = trigger_doc.get("responses", []) if trigger_doc else []
                
                # Logic Thông Minh: Nếu Type & Name đã có, không tạo rác trùng lặp
                exists = any(r["type"] == new_entry["type"] and r["name"] == new_entry["name"] for r in responses)
                if not exists:
                    responses.append(new_entry)
                    await self.db_triggers.update_one({"guild_id": interaction.guild_id, "trigger": trig}, {"$set": {"responses": responses}}, upsert=True)
                    self.update_cache(interaction.guild_id, trig, responses)

            embed = discord.Embed(title=f"{Emojis.BUOMA} khởi tạo mạch liên kết hoàn tất", description=f"Các từ khóa đã được liên kết với Hỏi Đáp.", color=0xe6e2dd)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"lỗi: `{str(e)}`", ephemeral=True)

    @qa_group.command(name="remove", description="Gỡ bỏ liên kết từ khóa (Hỗ trợ nhiều từ khóa bằng dấu phẩy)")
    @app_commands.describe(trigger="Từ khóa muốn gỡ (Dùng dấu phẩy ',' để gỡ nhiều)")
    @app_commands.autocomplete(trigger=qa_trigger_autocomplete)
    async def qa_remove(self, interaction: discord.Interaction, trigger: str):
        await interaction.response.defer(ephemeral=True)
        triggers_list = [t.strip().lower() for t in trigger.split(",") if t.strip()]
        try:
            for trig in triggers_list:
                if (await self.db_triggers.delete_one({"guild_id": interaction.guild_id, "trigger": trig})).deleted_count > 0:
                    self.update_cache(interaction.guild_id, trig, None)
            embed = discord.Embed(title=f"{Emojis.BUOMA} đã gỡ liên kết thành công", description=f"mạch nối đã bị chặt đứt.", color=0xe6e2dd)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"lỗi: `{str(e)}`", ephemeral=True)

    @qa_group.command(name="list", description="Bảng điều khiển kiểm soát toàn bộ biến số QA")
    @app_commands.describe(trigger="Nhập tên biến số để xem chi tiết (Tùy chọn)")
    @app_commands.autocomplete(trigger=qa_trigger_autocomplete)
    async def qa_list(self, interaction: discord.Interaction, trigger: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        try:
            guild_cache = self.cache.get(interaction.guild_id, {})
            if not guild_cache:
                return await interaction.followup.send(f"{Emojis.HOICHAM} chưa có từ khóa nào được thiết lập.", ephemeral=True)

            if trigger:
                trigger_lower = trigger.strip().lower()
                if trigger_lower not in guild_cache: return await interaction.followup.send("không tồn tại.", ephemeral=True)
                desc = "đang móc nối:\n\n"
                for i, r in enumerate(guild_cache[trigger_lower], 1):
                    desc += f"**{i}.** {'Văn bản' if r['type'] == 'text' else 'Embed'}: `{r['name']}`\n"
                return await interaction.followup.send(embed=discord.Embed(title=f"꒰ა chi tiết từ khóa: {trigger_lower} ໒꒱", description=desc, color=0xe6e2dd), ephemeral=True)

            all_fields = []
            for trig, responses in guild_cache.items():
                target = f"Văn bản: `{responses[0]['name']}`" if len(responses) == 1 and responses[0]["type"] == "text" else (f"Embed: `{responses[0]['name']}`" if len(responses) == 1 else f"Liên kết với {len(responses)} giá trị (Random)")
                all_fields.append({"name": f"Từ khóa: {trig}", "value": f"↳ {target}"})

            chunks = [all_fields[i:i + 10] for i in range(0, len(all_fields), 10)] or [[]]
            total_pages = len(chunks)

            if total_pages <= 1:
                embed = discord.Embed(title="꒰ა bảng điều khiển hỏi đáp yiyi ໒꒱", description="danh sách các từ khóa hỏi đáp đang hoạt động:", color=0xe6e2dd)
                for item in chunks[0]: embed.add_field(name=item["name"], value=item["value"], inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                view = QaListPagination(chunks, total_pages)
                msg = await interaction.followup.send(embed=view.build_embed(), view=view, ephemeral=True)
                view.message = msg
        except Exception as e:
            await interaction.followup.send(f"lỗi: `{str(e)}`", ephemeral=True)

async def setup(bot: commands.Bot):
    # 1. Nạp Cog để giữ nguyên hệ mạch Database
    cog = QASystem(bot)
    await bot.add_cog(cog)
    
    # 2. Rút /qa cũ ra và ghim vào cổng tổng /p
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn rác
        bot.tree.remove_command("qa")
        existing = next((cmd for cmd in p_cmd.commands if cmd.name == "qa"), None)
        if existing: p_cmd.remove_command("qa")
        
        # Tiêm mạch
        p_cmd.add_command(cog.qa_group)
        print("[LOAD] Success: commands.qa.qa_sys (Connected to /p Master Shield)", flush=True)
    else:
        print("[LOAD] Warning: Không tìm thấy /p. Cụm QA chạy độc lập.", flush=True)
