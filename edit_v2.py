import discord
from discord import app_commands
from discord.ext import commands


class EditV2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_data = {}

    # ===============================
    # 🔧 DATA HELPER
    # ===============================

    def get_guild_data(self, guild_id: int):
        if guild_id not in self.guild_data:
            self.guild_data[guild_id] = {
                "embeds": {},
                "message": {"content": None},
                "greet": {
                    "enabled": False,
                    "channel_id": None,
                    "embed_name": None,
                },
                "leave": {
                    "enabled": False,
                    "channel_id": None,
                    "embed_name": None,
                },
            }
        return self.guild_data[guild_id]

    def build_embed(self, data: dict):
        embed = discord.Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color", 0x2F3136),
        )
        if data.get("footer"):
            embed.set_footer(text=data["footer"])
        if data.get("image"):
            embed.set_image(url=data["image"])
        if data.get("thumbnail"):
            embed.set_thumbnail(url=data["thumbnail"])
        return embed

    # ===============================
    # 📦 SLASH GROUP
    # ===============================

    p = app_commands.Group(name="p", description="Panel system v2")

    # ===============================
    # 📦 EMBED COMMANDS
    # ===============================

    @p.command(name="embed_create")
    async def embed_create(self, interaction: discord.Interaction, name: str):
        data = self.get_guild_data(interaction.guild.id)

        if name in data["embeds"]:
            await interaction.response.send_message("Embed đã tồn tại.", ephemeral=True)
            return

        data["embeds"][name] = {
            "draft": {},
            "saved": {},
            "editor_message_id": None,
            "editor_channel_id": None,
            "bound_message": None,
        }

        await interaction.response.send_message(f"Đã tạo embed `{name}`", ephemeral=True)

    @p.command(name="embed_show")
    async def embed_show(self, interaction: discord.Interaction, name: str):
        data = self.get_guild_data(interaction.guild.id)

        if name not in data["embeds"]:
            await interaction.response.send_message("Không tìm thấy embed.", ephemeral=True)
            return

        saved = data["embeds"][name]["saved"]
        if not saved:
            await interaction.response.send_message("Embed chưa được save.", ephemeral=True)
            return

        embed = self.build_embed(saved)
        await interaction.response.send_message(embed=embed)

    # ===============================
    # 📨 MESSAGE SYSTEM
    # ===============================

    @p.command(name="message_set")
    async def message_set(self, interaction: discord.Interaction, content: str):
        data = self.get_guild_data(interaction.guild.id)
        data["message"]["content"] = content
        await interaction.response.send_message("Đã set message.", ephemeral=True)

    @p.command(name="message_bind")
    async def message_bind(self, interaction: discord.Interaction, name: str):
        data = self.get_guild_data(interaction.guild.id)

        if name not in data["embeds"]:
            await interaction.response.send_message("Không tìm thấy embed.", ephemeral=True)
            return

        data["embeds"][name]["bound_message"] = data["message"]["content"]
        await interaction.response.send_message("Đã bind message vào embed.", ephemeral=True)

    # ===============================
    # 👋 GREET SYSTEM
    # ===============================

    @p.command(name="greet_on")
    async def greet_on(self, interaction: discord.Interaction):
        data = self.get_guild_data(interaction.guild.id)
        data["greet"]["enabled"] = True
        await interaction.response.send_message("Greet đã bật.", ephemeral=True)

    @p.command(name="greet_off")
    async def greet_off(self, interaction: discord.Interaction):
        data = self.get_guild_data(interaction.guild.id)
        data["greet"]["enabled"] = False
        await interaction.response.send_message("Greet đã tắt.", ephemeral=True)

    @p.command(name="greet_channel")
    async def greet_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = self.get_guild_data(interaction.guild.id)
        data["greet"]["channel_id"] = channel.id
        await interaction.response.send_message("Đã set kênh greet.", ephemeral=True)

    @p.command(name="greet_embed")
    async def greet_embed(self, interaction: discord.Interaction, name: str):
        data = self.get_guild_data(interaction.guild.id)

        if name not in data["embeds"]:
            await interaction.response.send_message("Không tìm thấy embed.", ephemeral=True)
            return

        data["greet"]["embed_name"] = name
        await interaction.response.send_message("Đã set embed cho greet.", ephemeral=True)

    # ===============================
    # 👋 LEAVE SYSTEM
    # ===============================

    @p.command(name="leave_on")
    async def leave_on(self, interaction: discord.Interaction):
        data = self.get_guild_data(interaction.guild.id)
        data["leave"]["enabled"] = True
        await interaction.response.send_message("Leave đã bật.", ephemeral=True)

    @p.command(name="leave_off")
    async def leave_off(self, interaction: discord.Interaction):
        data = self.get_guild_data(interaction.guild.id)
        data["leave"]["enabled"] = False
        await interaction.response.send_message("Leave đã tắt.", ephemeral=True)

    @p.command(name="leave_channel")
    async def leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = self.get_guild_data(interaction.guild.id)
        data["leave"]["channel_id"] = channel.id
        await interaction.response.send_message("Đã set kênh leave.", ephemeral=True)

    @p.command(name="leave_embed")
    async def leave_embed(self, interaction: discord.Interaction, name: str):
        data = self.get_guild_data(interaction.guild.id)

        if name not in data["embeds"]:
            await interaction.response.send_message("Không tìm thấy embed.", ephemeral=True)
            return

        data["leave"]["embed_name"] = name
        await interaction.response.send_message("Đã set embed cho leave.", ephemeral=True)

    # ===============================
    # 🎉 EVENTS
    # ===============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = self.guild_data.get(member.guild.id)
        if not data:
            return

        greet = data["greet"]
        if not greet["enabled"]:
            return

        if not greet["channel_id"] or not greet["embed_name"]:
            return

        channel = self.bot.get_channel(greet["channel_id"])
        embed_data = data["embeds"][greet["embed_name"]]["saved"]

        if not embed_data:
            return

        embed = self.build_embed(embed_data)
        await channel.send(
            content=data["message"]["content"],
            embed=embed,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        data = self.guild_data.get(member.guild.id)
        if not data:
            return

        leave = data["leave"]
        if not leave["enabled"]:
            return

        if not leave["channel_id"] or not leave["embed_name"]:
            return

        channel = self.bot.get_channel(leave["channel_id"])
        embed_data = data["embeds"][leave["embed_name"]]["saved"]

        if not embed_data:
            return

        embed = self.build_embed(embed_data)
        await channel.send(
            content=data["message"]["content"],
            embed=embed,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EditV2(bot))
