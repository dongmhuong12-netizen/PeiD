import discord
from discord import app_commands
from discord.ext import commands

from core.booster_level_ui import BoosterLevelView
from core.booster_storage import (
    load_booster_levels,
    load_booster_config
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

        # load booster config
        config = load_booster_config(guild.id)

        if not config or not config.get("booster_role"):

            await interaction.response.send_message(
                "Server chưa thiết lập booster role. "
                "Hãy dùng lệnh `/p booster role` trước.",
                ephemeral=True
            )
            return

        booster_role = config["booster_role"]

        # load level config
        levels = load_booster_levels(guild.id)

        # nếu chưa có level config → tạo level 1 từ booster role
        if not levels:

            levels = [
                {
                    "role": booster_role,
                    "days": 0
                }
            ]

        view = BoosterLevelView(
            guild_id=guild.id,
            levels=[lvl.copy() for lvl in levels]
        )

        embed = view.build_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

        message = await interaction.original_response()
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(BoosterLevelCreate(bot))
