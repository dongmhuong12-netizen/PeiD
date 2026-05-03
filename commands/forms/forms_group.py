import discord
from discord import app_commands
from discord.ext import commands

from core.embed_storage import atomic_update_button
from core.cache_manager import get_raw, mark_dirty, update, save as force_save

FILE_KEY = "forms_configs"

class FormsGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="forms", description="Hệ thống biểu mẫu và đơn từ chuyên nghiệp")

    def _get_config(self, guild_id, embed_name):
        db = get_raw(FILE_KEY)
        if str(guild_id) not in db: db[str(guild_id)] = {}
        # Đảm bảo cấu trúc dữ liệu cho từng embed
        if embed_name not in db[str(guild_id)]:
            db[str(guild_id)][embed_name] = {
                "log_channel_id": None,
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
    # LỆNH 1: SETUP NỀN
    # =========================
    @app_commands.command(name="setup", description="Khởi tạo đơn và kênh nhận kết quả")
    async def setup_base(self, interaction: discord.Interaction, embed_name: str, log_channel_id: str):
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id, embed_name)
        config["log_channel_id"] = log_channel_id
        
        self._save_config(interaction.guild.id, embed_name, config)
        await force_save(FILE_KEY)
        await interaction.followup.send(f"✅ Đã thiết lập đơn cho Embed `{embed_name}`. Kết quả sẽ gửi về ID: {log_channel_id}")

    # =========================
    # LỆNH 2: THIẾT LẬP TRƯỜNG (1-5)
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
    # LỆNH 3: CẤY NÚT GỬI ĐƠN
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

# =========================
# Ổ CẮM EXTENSION (QUAN TRỌNG)
# =========================
async def setup(bot: commands.Bot):
    # Lấy lệnh cha /p đã được khai báo ở core.root
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Dọn dẹp nếu đã tồn tại để tránh lỗi trùng lặp khi reload
        existing = next((c for c in p_cmd.commands if c.name == "forms"), None)
        if existing: 
            p_cmd.remove_command("forms")
        
        # Tiêm nhánh /p forms vào
        p_cmd.add_command(FormsGroup())
        print("[LOAD] Success: commands.forms.forms_group", flush=True)
