import discord
from discord import app_commands
from discord.ext import commands
from utils.emojis import Emojis

class DevPrivateSpace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Mạch kết nối an toàn tương thích với MongoDB Atlas Wrapper của peiD
        self.db_premium = getattr(bot.db, "db", bot.db)["premium_users_sys"]
        # [CẤY MỚI] Sổ Nam Tào lưu trữ vòng đời danh mục phân khu
        self.db_spaces = getattr(bot.db, "db", bot.db)["private_spaces_sys"]

    async def has_premium_privilege(self, user_id: int) -> bool:
        """Kiểm toán quyền hạn thời gian thực: Boss tối cao hoặc User nằm trong sách trắng"""
        if user_id == self.bot.boss_id:
            return True
        record = await self.db_premium.find_one({"user_id": str(user_id)})
        return record is not None

    def get_unauthorized_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{Emojis.BUOMA} không được rồi, xin lỗi cậu nhe..",
            description="lệnh đặc cách kiến tạo phân khu này chỉ có người sáng lập mới có thể sử dụng.",
            color=0xe6e2dd
        )
        return embed

# =========================================================================
# MẠCH HỖ TRỢ AUTOCOMPLETE
# =========================================================================
async def user_autocomplete(interaction: discord.Interaction, current: str):
    if not interaction.guild:
        return []
    
    choices = []
    for member in interaction.guild.members:
        if current.lower() in member.name.lower() or (member.nick and current.lower() in member.nick.lower()):
            display_name = member.nick if member.nick else member.name
            choices.append(app_commands.Choice(name=f"{display_name} ({member.id})", value=str(member.id)))
        if len(choices) >= 25:
            break
    return choices

# =========================================================================
# 1. LỆNH CREATE: Kiến tạo danh mục, gán Role và lưu Database
# =========================================================================
@app_commands.command(name="space_create", description="[PREMIUM] Cấp danh mục 4 kênh tự quản và gán vai trò (nếu có)")
@app_commands.describe(
    user_or_id="Nhập ID số, tag @user trực tiếp hoặc gõ tên để tìm kiếm tự động",
    role_access="[Tùy chọn] Chọn Role để cấp đặc quyền này cho Owner và hiển thị danh mục"
)
@app_commands.autocomplete(user_or_id=user_autocomplete)
async def space_create_cmd(interaction: discord.Interaction, user_or_id: str, role_access: discord.Role = None):
    cog = interaction.client.get_cog("DevPrivateSpace")
    if not cog:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} nghẽn mạch cục bộ, module Space chưa lên đèn.", ephemeral=True)

    if not await cog.has_premium_privilege(interaction.user.id):
        return await interaction.response.send_message(embed=cog.get_unauthorized_embed(), ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    clean_id = "".join(filter(str.isdigit, user_or_id))
    target_member = guild.get_member(int(clean_id)) if clean_id else None
    
    if not target_member and clean_id:
        try:
            target_member = await guild.fetch_member(int(clean_id))
        except discord.NotFound:
            pass

    if not target_member:
        return await interaction.followup.send(embed=discord.Embed(
            title=f"{Emojis.HOICHAM} Không tìm thấy đối tượng",
            description="Hệ thống không thể định vị được Thành viên để cấp danh mục.",
            color=0xe6e2dd
        ))

    try:
        # Bảng phân quyền gốc cấp đặc quyền "Vua một cõi" cho Chủ sở hữu
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            target_member: discord.PermissionOverwrite(
                view_channel=True, manage_channels=True, manage_permissions=True,
                send_messages=True, embed_links=True, attach_files=True,
                read_message_history=True, manage_messages=True,
                connect=True, speak=True, mute_members=True, deafen_members=True, move_members=True
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_permissions=True)
        }

        role_log = ""
        if role_access:
            # Cho phép Role này được vào xem và kết nối chung
            overwrites[role_access] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True
            )
            # TỰ ĐỘNG CẤP ROLE CHO CHỦ SỞ HỮU (Try-Except chống rào cản phân cấp Role Discord)
            try:
                await target_member.add_roles(role_access)
                role_log = f"\n• **Huy hiệu được cấp:** {role_access.mention}"
            except discord.Forbidden:
                role_log = f"\n• **Huy hiệu:** ⚠️ Thất bại (Bot thiếu quyền cấp {role_access.mention})"

        # Xây dựng thực thể
        category_name = f"danh mục của {target_member.name}"
        new_category = await guild.create_category(name=category_name, overwrites=overwrites)

        for i in range(1, 4):
            await guild.create_text_channel(name=f"kênh-{i}", category=new_category)
        await guild.create_voice_channel(name="voice", category=new_category)

        # Lưu bản ghi vĩnh viễn lên đám mây MongoDB
        await cog.db_spaces.insert_one({
            "category_id": str(new_category.id),
            "owner_id": str(target_member.id),
            "role_id": str(role_access.id) if role_access else None,
            "category_name": category_name
        })

        embed_success = discord.Embed(
            title=f"{Emojis.BUOMA} Kiến tạo phân khu thành công!",
            description=f"Đã dựng xong phòng tự quản và cấy dữ liệu lên Sổ Nam Tào.\n\n"
                        f"• **Chủ nhà:** {target_member.mention}\n"
                        f"• **Mã danh mục:** `{new_category.id}`" + role_log,
            color=0xe6e2dd
        )
        await interaction.followup.send(embed=embed_success)

    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(
            title=f"{Emojis.HOICHAM} Nghẽn mạch hệ thống",
            description=f"Lỗi: `{str(e)}`", color=0xe6e2dd
        ))

# =========================================================================
# 2. LỆNH DELETE: Xóa sổ kênh ngầm, lột Role và gỡ bỏ dữ liệu
# =========================================================================
@app_commands.command(name="space_delete", description="[PREMIUM] Trục xuất danh mục, dọn dẹp kênh và thu hồi chức danh Chủ nhà")
@app_commands.describe(category_id="Nhập đúng mã ID của Danh mục sếp muốn xóa sổ")
async def space_delete_cmd(interaction: discord.Interaction, category_id: str):
    cog = interaction.client.get_cog("DevPrivateSpace")
    if not cog:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} module mất kết nối.", ephemeral=True)

    if not await cog.has_premium_privilege(interaction.user.id):
        return await interaction.response.send_message(embed=cog.get_unauthorized_embed(), ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    clean_cat_id = "".join(filter(str.isdigit, category_id))

    # 1. Quét đối chiếu Database
    target_space = await cog.db_spaces.find_one({"category_id": clean_cat_id})
    if not target_space:
        return await interaction.followup.send(embed=discord.Embed(
            title=f"{Emojis.HOICHAM} Cảnh báo xâm nhập chéo",
            description="ID Danh mục này không tồn tại trong Sổ Nam Tào của peiD. Hệ thống từ chối xóa để bảo vệ dữ liệu Server.",
            color=0xe6e2dd
        ))

    owner_id = target_space.get("owner_id")
    role_id = target_space.get("role_id")
    log_actions = []

    # 2. Thu hồi Role của Chủ nhà (Nếu có)
    if owner_id and role_id:
        target_member = interaction.guild.get_member(int(owner_id))
        if not target_member:
            try:
                target_member = await interaction.guild.fetch_member(int(owner_id))
            except discord.NotFound:
                target_member = None
        
        target_role = interaction.guild.get_role(int(role_id))
        if target_member and target_role:
            try:
                await target_member.remove_roles(target_role)
                log_actions.append(f"Đã thu hồi chức danh {target_role.mention} từ <@{owner_id}>")
            except Exception as e:
                log_actions.append(f"⚠️ Không thể thu hồi Role (Lỗi: {str(e)})")

    # 3. Trục xuất thực thể trên Server vật lý
    cat_obj = interaction.guild.get_channel(int(clean_cat_id))
    if not cat_obj:
        try:
            cat_obj = await interaction.guild.fetch_channel(int(clean_cat_id))
        except discord.NotFound:
            cat_obj = None

    if cat_obj and isinstance(cat_obj, discord.CategoryChannel):
        # Nã đạn diệt gọn các kênh con trước khi diệt danh mục
        for channel in cat_obj.channels:
            try: await channel.delete()
            except: pass
        
        try:
            await cat_obj.delete()
            log_actions.append(f"Đã dọn sạch 4 kênh và nổ tung Danh mục `{clean_cat_id}`")
        except Exception as e:
            log_actions.append(f"⚠️ Lỗi xóa thực thể danh mục: {str(e)}")
    else:
        log_actions.append("Thực thể danh mục không tồn tại trên Server (Có thể đã bị xóa bằng tay từ trước).")

    # 4. Gỡ bỏ khỏi Sổ Nam Tào
    await cog.db_spaces.delete_one({"category_id": clean_cat_id})
    log_actions.append("Đã xóa vĩnh viễn hồ sơ khỏi Cơ sở dữ liệu.")

    embed_done = discord.Embed(
        title=f"{Emojis.BUOMA} Xóa sổ phân khu thành công!",
        description="**Nhật ký chiến dịch dọn dẹp:**\n- " + "\n- ".join(log_actions),
        color=0xe6e2dd
    )
    await interaction.followup.send(embed=embed_done)

# =========================================================================
# 3. LỆNH LIST: Soi chiếu bảng điều khiển hệ thống
# =========================================================================
@app_commands.command(name="space_list", description="[PREMIUM] Soi chiếu bảng Sổ Nam Tào chứa các danh mục phân khu tự quản")
async def space_list_cmd(interaction: discord.Interaction):
    cog = interaction.client.get_cog("DevPrivateSpace")
    if not cog:
        return await interaction.response.send_message(f"{Emojis.HOICHAM} module mất kết nối.", ephemeral=True)

    if not await cog.has_premium_privilege(interaction.user.id):
        return await interaction.response.send_message(embed=cog.get_unauthorized_embed(), ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    
    # Hút toàn bộ dữ liệu vòng đời từ Đám mây
    cursor = cog.db_spaces.find({})
    lines = []
    
    async for sp in cursor:
        cat_id = sp.get("category_id", "N/A")
        own_id = sp.get("owner_id", "N/A")
        r_id = sp.get("role_id")
        
        role_txt = f"| Huy hiệu: <@&{r_id}>" if r_id else "| Tính chất: Ẩn danh tuyệt đối"
        lines.append(f"• Mục: <#{cat_id}> (`{cat_id}`) | Chủ: <@{own_id}> {role_txt}")

    if not lines:
        lines.append("Chưa có danh mục tự quản nào được hệ thống kiến tạo.")

    desc = "\n".join(lines)
    # Giới hạn an toàn chống tràn Field của Discord UI
    if len(desc) > 4000:
        desc = desc[:3900] + "\n\n... và nhiều danh mục khác nằm ngoài giới hạn quét trực quan."

    embed_list = discord.Embed(
        title=f"{Emojis.BUOMA} Bảng điều khiển phân khu tự quản",
        description=desc,
        color=0xe6e2dd
    )
    await interaction.followup.send(embed=embed_list)

async def setup(bot: commands.Bot):
    # Đăng ký Cog xử lý ngầm (Database & Auth)
    await bot.add_cog(DevPrivateSpace(bot))

    # Thuật toán nhúng Multi-IT kế thừa group /dev
    dev_group = None
    for cmd in bot.tree.get_commands():
        if cmd.name == "dev" and isinstance(cmd, app_commands.Group):
            dev_group = cmd
            break

    if dev_group:
        # Bơm 3 module tác chiến vào chung nhà /dev
        dev_group.add_command(space_create_cmd)
        dev_group.add_command(space_delete_cmd)
        dev_group.add_command(space_list_cmd)
        print("[LOAD] Success: commands.dev.dev_private_space (Space Engine Injected)", flush=True)
    else:
        print("[WARNING] Không tìm thấy group /dev. Lệnh Space đang chờ nạp lại!", flush=True)
