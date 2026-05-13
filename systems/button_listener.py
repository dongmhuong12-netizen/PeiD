import discord
from discord.ext import commands
from utils.emojis import Emojis
import asyncio

class ButtonListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """
        [PURE OMNI-ROUTER] Trạm trung chuyển tín hiệu thuần túy.
        Nhiệm vụ: Nhận tín hiệu 'yiyi:' và điều hướng đến các hệ thống chuyên biệt.
        """
        # 1. Lọc tương tác: Chỉ xử lý Nút bấm/Menu có tiền tố yiyi:
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id or not str(custom_id).startswith("yiyi:"):
            return

        # 2. Phân tách TOKEN: yiyi:[system]:[action]:[data]
        parts = custom_id.split(":")
        if len(parts) < 2:
            return

        system_type = parts[1] # ticket, forms, role, interaction, webhook...

        try:
            # --- SƠ ĐỒ ĐIỀU PHỐI TÍN HIỆU (TRAFFIC ROUTING) ---

            # 1. HỆ THỐNG TICKET
            if system_type == "ticket":
                from systems.ticket_system import handle_ticket_interaction
                await handle_ticket_interaction(interaction)

            # 2. HỆ THỐNG FORMS (MODAL)
            elif system_type == "forms":
                from systems.forms_system import handle_forms_interaction
                await handle_forms_interaction(interaction)

            # 3. HỆ THỐNG WEBHOOK (GIẢ DANH/TƯƠNG TÁC WEBHOOK)
            elif system_type == "webhook":
                from systems.webhook_system import handle_webhook_interaction
                await handle_webhook_interaction(interaction)

            # 4. HỆ THỐNG ROLE (SELF-ROLE/TOGGLE ROLE)
            elif system_type == "role":
                from systems.role_system import handle_role_interaction
                await handle_role_interaction(interaction)

            # 5. HỆ THỐNG MENU (DROPDOWN ROLE/SELECT)
            elif system_type == "menu":
                from systems.menu_system import handle_menu_interaction
                await handle_menu_interaction(interaction)

            # 6. HỆ THỐNG TƯƠNG TÁC OMNI (GACHA, VOTE, SECRET MESSAGE)
            elif system_type == "interaction":
                from systems.interaction_system import handle_omni_interaction
                await handle_omni_interaction(interaction)

            # 7. HỆ THỐNG UI UTILS (DISMISS, REFRESH, CLEAR)
            elif system_type == "ui":
                from systems.ui_system import handle_ui_interaction
                await handle_ui_interaction(interaction)

        except ImportError:
            # Xử lý khi sếp chưa kịp tạo các file .py tương ứng
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"{Emojis.HOICHAM} tính năng `{system_type}` đang được Yiyi nâng cấp, sếp chờ xíu nhé!", 
                    ephemeral=True
                )
        except Exception as e:
            # IT Pro: In log chi tiết để debug Cloud Sync
            print(f"[ROUTER CRITICAL] Lỗi tại trạm trung tâm ({system_type}): {e}", flush=True)
            if not interaction.response.is_done():
                try: 
                    await interaction.response.send_message(f"{Emojis.HOICHAM} lỗi đường truyền tín hiệu hoặc dữ liệu chưa kịp nạp!", ephemeral=True)
                except: 
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ButtonListener(bot))
    print("[LOAD] success: systems.button_listener (PURE OMNI-ROUTER)", flush=True)
