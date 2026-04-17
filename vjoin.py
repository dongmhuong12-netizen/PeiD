import discord
from discord import app_commands


@app_commands.command(name="vjoin")
async def vjoin(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("Bạn chưa ở voice", ephemeral=True)

    manager = interaction.client.voice_manager
    result = await manager.join(interaction, interaction.user.voice.channel)

    if result == True:
        await interaction.response.send_message("Đã vào voice")
    elif result == "COOLDOWN":
        await interaction.response.send_message("Đang cooldown", ephemeral=True)
    else:
        await interaction.response.send_message(f"Lỗi: {result}", ephemeral=True)
