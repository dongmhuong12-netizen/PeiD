import discord
from discord import app_commands

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            raise app_commands.CheckFailure("Lệnh chỉ dùng trong server.")

        if interaction.user.guild_permissions.administrator:
            return True

        raise app_commands.CheckFailure("Bạn không có quyền Administrator.")
    return app_commands.check(predicate)


def is_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == interaction.client.owner_id:
            return True
        raise app_commands.CheckFailure("Chỉ bot owner mới dùng được.")
    return app_commands.check(predicate)
