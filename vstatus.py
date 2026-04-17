import discord
from discord import app_commands


@app_commands.command(name="vstatus")
async def vstatus(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    if not vc:
        return await interaction.response.send_message("Bot không ở voice")

    await interaction.response.send_message(
        f"Voice: {vc.channel.name}\nStatus: Connected"
    )
