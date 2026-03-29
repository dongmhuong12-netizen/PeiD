# commands/booster/lv_create.py
import discord
from discord import app_commands
from discord.ext import commands

from core.booster_level_ui import open_booster_level_ui
from core.booster_storage import (
    get_levels,
    get_guild_config
)


class BoosterLevelCreate(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="create",
        description="Mở bảng chỉnh Booster Level"
    )
    async def booster_lv_create(self, interaction: discord.Interaction):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Lệnh này chỉ dùng trong server.",
                ephemeral=True
            )
            return

        # =========================
        # CHECK PERMISSION
        # =========================
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Bạn cần quyền Manage Server để dùng lệnh này.",
                ephemeral=True
            )
            return

        # =========================
        # LOAD CONFIG
        # =========================
        config = await get_guild_config(guild.id)

        if not config or not config.get("booster_role"):
            await interaction.response.send_message(
                "Server chưa thiết lập booster role. "
                "Hãy dùng lệnh `/p booster role` trước.",
                ephemeral=True
            )
            return

        booster_role = config["booster_role"]

        # =========================
        # LOAD LEVELS
        # =========================
        levels = await get_levels(guild.id)

        # nếu chưa có → tạo level 1
        if not levels:
            levels = [
                {
                    "role": booster_role,
                    "days": 0
                }
            ]

        # =========================
        # OPEN UI (FIXED)
        # =========================
        await interaction.response.defer(ephemeral=True)

        await open_booster_level_ui(
            self.bot,
            interaction.followup,
            guild_id=guild.id,
            levels=[lvl.copy() for lvl in levels],
            booster_role=booster_role
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BoosterLevelCreate(bot))
