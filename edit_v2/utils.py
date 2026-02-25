import discord
from datetime import datetime

def success_embed(description: str):
    return discord.Embed(
        description=f"✅ {description}",
        color=discord.Color.green()
    )

def error_embed(description: str):
    return discord.Embed(
        description=f"❌ {description}",
        color=discord.Color.red()
    )

def info_embed(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )
    return embed
