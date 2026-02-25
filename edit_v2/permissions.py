import discord
from discord import app_commands

def is_mod_or_admin():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            raise app_commands.CheckFailure("Chỉ dùng trong server.")

        if interaction.user.guild_permissions.administrator:
            return True

        role_id = await interaction.client.get_cog("EditV2").db.fetchone(
            "SELECT mod_role_id FROM guild_config WHERE guild_id = ?",
            (interaction.guild.id,)
        )

        if role_id and role_id[0]:
            role = interaction.guild.get_role(role_id[0])
            if role in interaction.user.roles:
                return True

        raise app_commands.CheckFailure("Bạn không có quyền dùng lệnh này.")
    return app_commands.check(predicate)
