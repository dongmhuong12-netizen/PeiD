import discord
from discord.ext import commands
from discord import app_commands
import re
import traceback
import asyncio

from core.variable_engine import apply_variables 
from utils.emojis import Emojis

def parse_time_to_seconds(time_str: str) -> int:
    match = re.match(r'^(\d+)(s|m)$', time_str.lower().strip())
    if not match:
        return -1
    amount = int(match.group(1))
    unit = match.group(2)
    return amount * 60 if unit == 'm' else amount

# ==========================================
# KHỐI MODAL (MENU CHỈNH SỬA UI/UX PREMIUM)
# ==========================================

class VoiceTagBasicModal(discord.ui.Modal, title="Tùy chỉnh Thông báo Voice Basic"):
    join_text = discord.ui.TextInput(
        label="Văn bản khi Vào Voice (Join)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )
    leave_text = discord.ui.TextInput(
        label="Văn bản khi Rời Voice (Leave)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    def __init__(self, cog, guild_id: int, current_join: str, current_leave: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.join_text.default = current_join
        self.leave_text.default = current_leave

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.db.update_one(
            {"guild_id": self.guild_id},
            {"$set": {
                "join_text": self.join_text.value,
                "leave_text": self.leave_text.value
            }},
            upsert=True
        )
        await interaction.response.send_message(f"{Emojis.BUOMA} Đã cập nhật văn bản Basic thành công!", ephemeral=True)


class VoiceTagMoveModal(discord.ui.Modal, title="Tùy chỉnh Thông báo Nhảy Voice"):
    move_old_text = discord.ui.TextInput(
        label="Báo ở Kênh Cũ (Kênh bị rời đi)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )
    move_new_text = discord.ui.TextInput(
        label="Báo ở Kênh Mới (Kênh vừa đến)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    def __init__(self, cog, guild_id: int, current_old: str, current_new: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.move_old_text.default = current_old
        self.move_new_text.default = current_new

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.db.update_one(
            {"guild_id": self.guild_id},
            {"$set": {
                "move_old_text": self.move_old_text.value,
                "move_new_text": self.move_new_text.value
            }},
            upsert=True
        )
        await interaction.response.send_message(f"{Emojis.BUOMA} Đã cập nhật văn bản Nhảy Voice thành công!", ephemeral=True)


# ==========================================
# KHỐI MODULE CHÍNH (COG)
# ==========================================

class VoiceTag(commands.GroupCog, group_name="voicetag", group_description="Hệ thống Thông báo Voice Premium"):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db.db['voice_tag_config'] 
        self._pending_tasks = {} # [BỘ ĐỆM ĐA LUỒNG] Lưu trữ các luồng thông báo chờ xác thực

        # Khôi phục nguyên gốc text mặc định
        self.default_configs = {
            "status": False,
            "notify_move": False,
            "autodelete_status": False,
            "autodelete_delay": 0,
            "join_text": "{user} đã tham gia kênh.",
            "leave_text": "{user} đã rời khỏi kênh.",
            "move_old_text": "{user} đã rời khỏi kênh và tham gia kênh {voice_new}.",
            "move_new_text": "{user} vừa rời kênh {voice_old} và đã tham gia kênh này."
        }

    async def get_config(self, guild_id: int) -> dict:
        data = await self.db.find_one({"guild_id": guild_id})
        if not data:
            return self.default_configs.copy()
        
        config = self.default_configs.copy()
        config.update(data)
        return config

    # ------------------------------------------
    # LỆNH 1: BẬT / TẮT HỆ THỐNG TRUNG TÂM
    # ------------------------------------------
    @app_commands.command(name="toggle", description="Bật hoặc tắt hệ thống thông báo Voice")
    @app_commands.describe(status="Công tắc hệ thống chung", notify_move="Bật báo nhảy Voice (Rời phòng A sang phòng B)")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Bật", value=1),
            app_commands.Choice(name="Tắt", value=0)
        ],
        notify_move=[
            app_commands.Choice(name="Bật", value=1),
            app_commands.Choice(name="Tắt", value=0)
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def toggle_sys(self, interaction: discord.Interaction, status: int, notify_move: int = None):
        update_data = {"status": bool(status)}
        if notify_move is not None:
            update_data["notify_move"] = bool(notify_move)

        await self.db.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": update_data},
            upsert=True
        )
        
        st_text = "BẬT" if status else "TẮT"
        mv_text = f" | Nhảy Voice: {'BẬT' if notify_move else 'TẮT'}" if notify_move is not None else ""
        await interaction.response.send_message(f"{Emojis.BUOMA} Trạng thái Voice Tag: **{st_text}**{mv_text}", ephemeral=True)

    # ------------------------------------------
    # LỆNH 2: CẤU HÌNH AUTO-DELETE
    # ------------------------------------------
    @app_commands.command(name="autodelete", description="Cài đặt tự động xóa tin nhắn thông báo")
    @app_commands.describe(status="Bật hoặc tắt", delay="Thời gian (VD: 10s, 5m)")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Bật", value=1),
            app_commands.Choice(name="Tắt", value=0)
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def auto_delete(self, interaction: discord.Interaction, status: int, delay: str = None):
        update_data = {"autodelete_status": bool(status)}
        
        if status == 1:
            if not delay:
                return await interaction.response.send_message(f"{Emojis.HOICHAM} Bạn cần nhập thời gian `delay` (VD: 10s, 1m) khi bật!", ephemeral=True)
            
            seconds = parse_time_to_seconds(delay)
            if seconds < 0:
                return await interaction.response.send_message(f"{Emojis.HOICHAM} Sai định dạng thời gian. Hãy dùng số kèm theo `s` (giây) hoặc `m` (phút). VD: 30s, 2m.", ephemeral=True)
            if seconds > 3600:
                return await interaction.response.send_message(f"{Emojis.HOICHAM} Thời gian xóa tối đa là 60m (3600s).", ephemeral=True)
                
            update_data["autodelete_delay"] = seconds

        await self.db.update_one({"guild_id": interaction.guild.id}, {"$set": update_data}, upsert=True)
        
        if status == 1:
            await interaction.response.send_message(f"{Emojis.BUOMA} Đã BẬT dọn dẹp tin nhắn. Tin sẽ tự xóa sau **{delay}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{Emojis.BUOMA} Đã TẮT dọn dẹp tin nhắn.", ephemeral=True)

    # ------------------------------------------
    # LỆNH 3: MENU TEXT BASIC
    # ------------------------------------------
    @app_commands.command(name="menu_basic", description="Tùy chỉnh nội dung khi vào/rời Voice")
    @app_commands.default_permissions(manage_guild=True)
    async def menu_basic(self, interaction: discord.Interaction):
        config = await self.get_config(interaction.guild.id)
        modal = VoiceTagBasicModal(
            cog=self, 
            guild_id=interaction.guild.id,
            current_join=config["join_text"],
            current_leave=config["leave_text"]
        )
        await interaction.response.send_modal(modal)

    # ------------------------------------------
    # LỆNH 4: MENU TEXT NHẢY VOICE
    # ------------------------------------------
    @app_commands.command(name="menu_move", description="Tùy chỉnh nội dung báo nhảy Voice")
    @app_commands.default_permissions(manage_guild=True)
    async def menu_move(self, interaction: discord.Interaction):
        config = await self.get_config(interaction.guild.id)
        modal = VoiceTagMoveModal(
            cog=self, 
            guild_id=interaction.guild.id,
            current_old=config["move_old_text"],
            current_new=config["move_new_text"]
        )
        await interaction.response.send_modal(modal)


    # ==========================================
    # CỖ MÁY THỰC THI (ĐƯỢC GỌI SAU KHI QUA BỘ LỌC)
    # ==========================================
    async def execute_voice_notification(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        try:
            # Nghỉ nhịp 0.7s để hứng mọi tín hiệu API dồn dập (True Debounce Sweep)
            await asyncio.sleep(0.7)

            config = await self.get_config(member.guild.id)
            if not config["status"]:
                return

            del_time = config["autodelete_delay"] if config["autodelete_status"] else None
            ninja_mode = {"silent": True, "allowed_mentions": discord.AllowedMentions(users=False)}

            # === MẠCH 1: NHẢY VOICE (MOVE) ===
            if before.channel and after.channel and before.channel != after.channel:
                if config["notify_move"]:
                    text_old = apply_variables(
                        config["move_old_text"], member.guild, member, 
                        old_channel=before.channel, new_channel=after.channel
                    )
                    await before.channel.send(text_old, delete_after=del_time, **ninja_mode)

                    text_new = apply_variables(
                        config["move_new_text"], member.guild, member, 
                        old_channel=before.channel, new_channel=after.channel
                    )
                    await after.channel.send(text_new, delete_after=del_time, **ninja_mode)
                else:
                    leave_tx = apply_variables(config["leave_text"], member.guild, member, channel=before.channel)
                    await before.channel.send(leave_tx, delete_after=del_time, **ninja_mode)
                    
                    join_tx = apply_variables(config["join_text"], member.guild, member, channel=after.channel)
                    await after.channel.send(join_tx, delete_after=del_time, **ninja_mode)

            # === MẠCH 2: BASIC JOIN ===
            elif not before.channel and after.channel:
                join_tx = apply_variables(config["join_text"], member.guild, member, channel=after.channel)
                await after.channel.send(join_tx, delete_after=del_time, **ninja_mode)

            # === MẠCH 3: BASIC LEAVE ===
            elif before.channel and not after.channel:
                leave_tx = apply_variables(config["leave_text"], member.guild, member, channel=before.channel)
                await before.channel.send(leave_tx, delete_after=del_time, **ninja_mode)

        except asyncio.CancelledError:
            # Bot âm thầm hủy luồng nếu phát hiện sự kiện này đã lỗi thời (Khách bị bế đi phòng khác)
            pass
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"[VOICE TAG ERROR] Lỗi tại server {member.guild.name}: {e}")
            traceback.print_exc()
        finally:
            # Dọn dẹp RAM sau khi chạy xong
            if member.id in self._pending_tasks and self._pending_tasks[member.id] == asyncio.current_task():
                del self._pending_tasks[member.id]


    # ==========================================
    # CẢM BIẾN BẮT LUỒNG VÀ PHÂN LUỒNG (TRUE DEBOUNCE)
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
            
        if before.channel == after.channel:
            return

        # 1. Hủy bỏ ngay lập tức thông báo cũ nếu người dùng nhảy kênh liên tục
        if member.id in self._pending_tasks:
            self._pending_tasks[member.id].cancel()

        # 2. Tạo một luồng chờ mới cho sự kiện hiện tại
        task = asyncio.create_task(self.execute_voice_notification(member, before, after))
        self._pending_tasks[member.id] = task


async def setup(bot):
    await bot.add_cog(VoiceTag(bot))
