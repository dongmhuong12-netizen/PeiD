import discord

class PermissionManager:

    @staticmethod
    async def is_admin(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator

    @staticmethod
    async def is_mod(interaction: discord.Interaction):
        perms = interaction.user.guild_permissions
        return perms.manage_guild or perms.kick_members or perms.ban_members
