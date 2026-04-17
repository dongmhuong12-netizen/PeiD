import discord
from discord import app_commands


@app_commands.command(name="vleave")
async def vleave(interaction: discord.Interaction):
    manager = interaction.client.voice_manager
    result = await manager.leave(interaction.guild)

    if result == True:
        await interaction.response.send_message("Đã rời voice")
    else:
        await interaction.response.send_message(f"Lỗi: {result}", ephemeral=True)
