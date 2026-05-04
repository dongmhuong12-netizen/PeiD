import discord
from discord import app_commands
from discord.ext import commands
import re # Tiêm bộ lọc ký tự lạ

from core.embed_storage import atomic_update_button
from core.cache_manager import get_raw, mark_dirty, update, save as force_save

FILE_KEY = "forms_configs"

class FormsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="forms", description="Hệ thống biểu mẫu và đơn từ chuyên nghiệp")

    def _sanitize_id(self, input_str: str):
        """[BỘ LỌC YIYI] Gọt sạch tag kênh/role chỉ lấy số ID"""
        if not input_str: return ""
        return re.sub(r'\D', '', input_str)

    def _get_config(self, guild_id, embed_name):
        db = get_raw(FILE_KEY)
        if str(guild_id) not in db: db[str(guild_id)] = {}
        if embed_name not in db[str(guild_id)]:
            db[str(guild_id)][embed_name] = {
                "log_channel_id": None,
                "form_title": None, # Thêm mạch lưu tiêu đề đơn
                "fields": {}
            }
        return db[str(guild_id)][embed_name]

    def _save_config(self, guild_id, embed_name, config):
        db = get_raw(FILE_KEY)
        if str(guild_id) not in db: db[str(guild_id)] = {}
        db[str(guild_id)][embed_name] = config
        update(FILE_KEY, db)
        mark_dirty(FILE_KEY)

    # =========================
    # LỆNH 1: SETUP NỀN (ĐÃ CẬP NHẬT)
    # =========================
    @app_commands.command(name="setup", description="Khởi tạo đơn, tiêu đề và kênh nhận kết quả")
    @app_commands.describe(
        embed_name="Tên embed gắn đơn",
        log_channel_id="ID hoặc Tag kênh nhận kết quả",
        form_title="Tiêu đề hiển thị trên đơn (Ví dụ: ĐƠN ỨNG TUYỂN STAFF)"
    )
    async def setup_base(self, interaction: discord.Interaction, embed_name: str, log_channel_id: str, form_title: str = None):
        await interaction.response.defer(ephemeral=True)
        
        # 1. Gọt sạch ID kênh log
        clean_log_id = self._sanitize_id(log_channel_id)
        
        config = self._get_config(interaction.guild.id, embed_name)
        config["log_channel_id"] = clean_log_id
        config["form_title"] = form_title # Lưu tiêu đề sếp muốn
        
        self._save_config(interaction.guild.id, embed_name, config)
        await force_save(FILE_KEY)
        
        res_msg = f"✅ Đã thiết lập đơn cho Embed `{embed_name}`.\n• Kênh log: <#{clean_log_id}>"
        if form_title:
            res_msg += f"\n• Tiêu đề đơn: **{form_title}**"
            
        await interaction.followup.send(res_msg)

    # =========================
    # LỆNH 2: THIẾT LẬP TRƯỜNG (1-5) - GIỮ NGUYÊN
    # =========================
    @app_commands.command(name="field", description="Cấu hình nội dung cho từng ô nhập liệu (Tối đa 5)")
    @app_commands.choices(slot=[
        app_commands.Choice(name="Trường 1", value=1),
        app_commands.Choice(name="Trường 2", value=2),
        app_commands.Choice(name="Trường 3", value=3),
        app_commands.Choice(name="Trường 4", value=4),
        app_commands.Choice(name="Trường 5", value=5),
    ])
    async def field(self, interaction: discord.Interaction, embed_name: str, slot: int, label: str, placeholder: str = "Nhập nội dung...", required: bool = True):
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id, embed_name)
        
        config["fields"][str(slot)] = {
            "label": label[:45], 
            "placeholder": placeholder[:100],
            "required": required
        }
        
        self._save_config(interaction.guild.id, embed_name, config)
        await force_save(FILE_KEY)
        await interaction.followup.send(f"✅ Đã cập nhật **Trường {slot}** cho đơn `{embed_name}`.")

    # =========================
    # LỆNH 3: CẤY NÚT GỬI ĐƠN - GIỮ NGUYÊN
    # =========================
    @app_commands.command(name="apply", description="Gắn nút gửi đơn vào Embed")
    async def apply(self, interaction: discord.Interaction, embed_name: str, label: str = "Gửi đơn đăng ký"):
        await interaction.response.defer(ephemeral=True)
        
        btn_data = {
            "type": "button",
            "style": "success",
            "label": label,
            "emoji": "📝",
            "custom_id": f"yiyi:forms:open:{embed_name}", 
            "system": "forms"
        }

        success = await atomic_update_button(interaction.guild.id, embed_name, action="add", button_data=btn_data)
        if success:
            await interaction.followup.send(f"✅ Đã gắn nút gửi đơn vào `{embed_name}`!")
        else:
            await interaction.followup.send("❌ Gắn nút thất bại. Kiểm tra tên Embed hoặc số lượng nút sếp nhé.")

async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        existing = next((c for c in p_cmd.commands if c.name == "forms"), None)
        if existing: p_cmd.remove_command("forms")
        p_cmd.add_command(FormsGroup())
        print("[LOAD] Success: commands.forms.forms_group (Custom Title)", flush=True)
