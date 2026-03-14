import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.greet_storage import get_section, update_guild_config
from core.embed_storage import load_embed
from core.greet_leave import send_config_message

from core.booster_engine import assign_correct_level
from core.booster_storage import load_booster_levels
from core.booster_level_ui import BoosterLevelView


# ======================
# BOOSTER GROUP
# ======================

class BoosterGroup(app_commands.Group):

    def __init__(self):
        super().__init__(
            name="booster",
            description="Hệ thống xử lý khi thành viên Boost server"
        )

    @app_commands.command(
        name="channel",
        description="Đặt kênh gửi thông báo khi có người boost"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, channel_id: str):

        if not channel_id.isdigit():
            await interaction.response.send_message(
                "ID kênh không hợp lệ.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(int(channel_id))

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Không tìm thấy text channel.",
                ephemeral=True
            )
            return

        update_guild_config(
            interaction.guild.id,
            "booster",
            "channel",
            channel.id
        )

        await interaction.response.send_message(
            f"Đặt kênh Boost thành công: {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(
        name="message",
        description="Đặt nội dung tin nhắn khi có người boost"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, text: str):

        update_guild_config(
            interaction.guild.id,
            "booster",
            "message",
            text
        )

        await interaction.response.send_message(
            f"Đặt nội dung Boost thành công: {text}",
            ephemeral=True
        )

    @app_commands.command(
        name="embed",
        description="Gán embed đã tạo cho thông báo booster"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def embed(self, interaction: discord.Interaction, name: str):

        if not load_embed(interaction.guild.id, name):

            await interaction.response.send_message(
                f"Embed `{name}` không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(
            interaction.guild.id,
            "booster",
            "embed",
            name
        )

        await interaction.response.send_message(
            f"Đặt embed Boost thành công: `{name}`",
            ephemeral=True
        )

    @app_commands.command(
        name="role",
        description="Đặt role sẽ được gán cho người boost"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role_input: str):

        guild = interaction.guild

        if role_input.startswith("<@&") and role_input.endswith(">"):
            role_id = role_input.replace("<@&", "").replace(">", "")
        else:
            role_id = role_input

        if not role_id.isdigit():
            await interaction.response.send_message(
                "ID Role không hợp lệ.",
                ephemeral=True
            )
            return

        role = guild.get_role(int(role_id))

        if not role:
            await interaction.response.send_message(
                "Role không tồn tại.",
                ephemeral=True
            )
            return

        update_guild_config(
            guild.id,
            "booster",
            "role",
            role.id
        )

        await interaction.response.send_message(
            f"Đặt role Boost thành công: {role.mention}",
            ephemeral=True
        )

    # ======================
    # BOOSTER LEVEL EDITOR
    # ======================

    @app_commands.command(
        name="level",
        description="Mở bảng chỉnh Booster Level"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def level(self, interaction: discord.Interaction):

        guild = interaction.guild

        config = get_section(guild.id, "booster")
        booster_role = config.get("role")

        if not booster_role:

            await interaction.response.send_message(
                "Server chưa thiết lập booster role. "
                "Hãy dùng lệnh `/p booster role` trước.",
                ephemeral=True
            )
            return

        levels = load_booster_levels(guild.id)

        if not levels:

            levels = [
                {
                    "role": booster_role,
                    "days": 0
                }
            ]

        view = BoosterLevelView(
            guild_id=guild.id,
            levels=[lvl.copy() for lvl in levels]
        )

        embed = view.build_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

        message = await interaction.original_response()
        view.message = message

    @app_commands.command(
        name="test",
        description="Kiểm tra hệ thống booster"
    )
    async def test(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        config = get_section(guild.id, "booster")

        role_id = config.get("role")
        role = guild.get_role(role_id) if role_id else None

        if role:

            if role.position >= bot_member.top_role.position:

                await interaction.followup.send(
                    "Role bot thấp hơn role booster.",
                    ephemeral=True
                )
                return

            try:
                await member.add_roles(role, reason="Booster Test")

            except Exception as e:

                await interaction.followup.send(
                    f"Lỗi khi gán role: {e}",
                    ephemeral=True
                )
                return

        success = await send_config_message(guild, member, "booster")

        if success:

            await interaction.followup.send(
                "Test Boost thành công.",
                ephemeral=True
            )

        else:

            await interaction.followup.send(
                "Thiếu cấu hình booster.",
                ephemeral=True
            )


# ======================
# LISTENER
# ======================

class BoosterListener(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot
        self._startup_done = False
        self.booster_sync.start()

    def cog_unload(self):

        self.booster_sync.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        if after.bot:
            return

        if not before.premium_since and after.premium_since:
            await self.handle_boost(after, True)

        elif before.premium_since and not after.premium_since:
            await self.handle_boost(after, False)

    async def handle_boost(self, member: discord.Member, boosted: bool):

        guild = member.guild
        config = get_section(guild.id, "booster")

        role_id = config.get("role")
        role = guild.get_role(role_id) if role_id else None

        if not role:
            return

        bot_member = guild.me
        if not bot_member:
            return

        if role.position >= bot_member.top_role.position:
            return

        try:

            if boosted and role not in member.roles:

                await member.add_roles(role, reason="Server Boost")

            elif not boosted and role in member.roles:

                await member.remove_roles(role, reason="Boost Ended")

        except discord.Forbidden:
            return

        if boosted:

            await send_config_message(
                guild,
                member,
                "booster"
            )

        if member.premium_since:

            try:
                await assign_correct_level(member)
            except Exception:
                pass

    @tasks.loop(minutes=30)
    async def booster_sync(self):

        for guild in self.bot.guilds:

            if guild.unavailable:
                continue

            config = get_section(guild.id, "booster")

            role_id = config.get("role")
            role = guild.get_role(role_id) if role_id else None

            if not role:
                continue

            bot_member = guild.me
            if not bot_member:
                continue

            if role.position >= bot_member.top_role.position:
                continue

            boosters = guild.premium_subscribers

            if not boosters:
                continue

            for member in boosters:

                if member.bot:
                    continue

                try:

                    if role not in member.roles:

                        await member.add_roles(
                            role,
                            reason="Booster Sync"
                        )

                except discord.Forbidden:
                    pass

                if member.premium_since:

                    try:
                        await assign_correct_level(member)
                    except Exception:
                        pass

                await asyncio.sleep(0.2)

    @booster_sync.before_loop
    async def before_booster_sync(self):

        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):

        if self._startup_done:
            return

        self._startup_done = True

        for guild in self.bot.guilds:

            boosters = guild.premium_subscribers

            if not boosters:
                continue

            for member in boosters:

                if member.bot:
                    continue

                try:
                    await assign_correct_level(member)
                except Exception:
                    pass

                await asyncio.sleep(0.2)


async def setup(bot):

    await bot.add_cog(BoosterListener(bot))
