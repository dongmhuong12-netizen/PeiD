import discord
from discord import app_commands
from discord.ext import commands

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message


# ======================
# BOOSTER GROUP
# ======================

class BoosterGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="booster", description="Booster system")

    @app_commands.command(name="channel", description="Set booster channel (Channel ID)")
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_id: str):

        if not channel_id.isdigit():
            await interaction.response.send_message("Channel ID không hợp lệ.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Không tìm thấy text channel.", ephemeral=True)
            return

        update_guild_config(interaction.guild.id, "booster", "channel", channel.id)

        await interaction.response.send_message(
            f"Đã set kênh booster: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(name="message", description="Set booster message")
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):

        update_guild_config(interaction.guild.id, "booster", "message", text)

        await interaction.response.send_message(
            "Đã set message booster.",
            ephemeral=True
        )

    @app_commands.command(name="embed", description="Set booster embed")
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(name):
            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(interaction.guild.id, "booster", "embed", name)

        await interaction.response.send_message(
            f"Đã set embed booster: `{name}`",
            ephemeral=True
        )

    @app_commands.command(name="role", description="Set booster role")
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role_input: str):

        guild = interaction.guild

        # Nếu là mention <@&123>
        if role_input.startswith("<@&") and role_input.endswith(">"):
            role_id = role_input.replace("<@&", "").replace(">", "")
        else:
            role_id = role_input

        if not role_id.isdigit():
            await interaction.response.send_message(
                "Role ID không hợp lệ.",
                ephemeral=True
            )
            return

        role = guild.get_role(int(role_id))

        if not role:
            await interaction.response.send_message(
                "Không tìm thấy role.",
                ephemeral=True
            )
            return

        update_guild_config(guild.id, "booster", "role", role.id)

        await interaction.response.send_message(
            f"Đã set booster role: {role.mention}",
            ephemeral=True
        )

    @app_commands.command(name="test", description="Test booster system")
    async def test(self, interaction: discord.Interaction):

        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        config = get_section(guild.id, "booster")

        role_id = config.get("role")
        role = guild.get_role(role_id) if role_id else None

        if role:
            if role >= bot_member.top_role:
                await interaction.response.send_message(
                    "Bot không thể gán role này vì role cao hơn hoặc bằng role của bot.",
                    ephemeral=True
                )
                return

            if role in member.roles:
                await interaction.response.send_message(
                    "Bạn đã có role này rồi.",
                    ephemeral=True
                )
                return

            try:
                await member.add_roles(role, reason="Booster Test")
            except Exception as e:
                await interaction.response.send_message(
                    f"Lỗi khi gán role: {e}",
                    ephemeral=True
                )
                return

        success = await send_config_message(guild, member, "booster")

        if not success:
            await interaction.followup.send(
                "Chưa cấu hình booster.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Đã test booster (role + message).",
                ephemeral=True
            )


# ======================
# LISTENER
# ======================

class BoosterListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        # Bắt đầu boost
        if not before.premium_since and after.premium_since:
            await self.handle_boost(after, True)

        # Hết boost
        if before.premium_since and not after.premium_since:
            await self.handle_boost(after, False)

    async def handle_boost(self, member: discord.Member, boosted: bool):

        config = get_section(member.guild.id, "booster")

        role_id = config.get("role")
        role = member.guild.get_role(role_id) if role_id else None

        if boosted and role:
            try:
                await member.add_roles(role, reason="Server Boost")
            except:
                pass

        if not boosted and role:
            try:
                await member.remove_roles(role, reason="Boost Ended")
            except:
                pass

        await send_config_message(member.guild, member, "booster")
