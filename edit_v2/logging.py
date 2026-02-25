import discord

class LogSystem:

    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def log_action(self, guild: discord.Guild, action: str, user_id: int, moderator_id: int):

        config = await self.db.fetchone(
            "SELECT log_channel_id FROM guild_config WHERE guild_id = ?",
            (guild.id,)
        )

        if not config or not config[0]:
            return

        channel = guild.get_channel(config[0])
        if not channel:
            return

        embed = discord.Embed(
            title="Moderation Log",
            description=f"**Action:** {action}",
            color=discord.Color.orange()
        )
        embed.add_field(name="User ID", value=str(user_id))
        embed.add_field(name="Moderator ID", value=str(moderator_id))

        await channel.send(embed=embed)
