import discord

def success_embed(message: str):
    return discord.Embed(
        description=f"✅ {message}",
        color=discord.Color.green()
    )

def error_embed(message: str):
    return discord.Embed(
        description=f"❌ {message}",
        color=discord.Color.red()
    )

def info_embed(message: str):
    return discord.Embed(
        description=f"ℹ {message}",
        color=discord.Color.blurple()
    )
