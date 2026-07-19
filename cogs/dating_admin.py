import discord
from core.dating_permissions import authority_of, list_staff, promote_father, demote_father, set_cupid_permissions, make_full_cupid, ALL_PERMISSIONS, PERMISSION_LABEL, PERMISSION_HINT, RANK_LABEL
from core.dating_storage import get_guild_config, db
from core.dating_moderation import reset_user_swipes, resolve_reports, open_reports, ban_profile, unban_profile
from core.dating_report_reasons import reason_label
from ui.dating_theme import COLOR, GLYPH, sub
from ui.dating_profile_card import notice
from core.dating_superlikes import give_superlikes, get_balance, recent_grants, grants_by_staff

# Dictionary thay thế cho CUPID_REQUIRED
CUPID_REQUIRED = {
    "give": "GIVE_SUPERLIKE",
    "balance": "GIVE_SUPERLIKE",
    "reports": "REVIEW_REPORTS",
    "resolve": "REVIEW_REPORTS",
    "ban": "MODERATE_PROFILE",
    "unban": "MODERATE_PROFILE",
    "status": "VIEW_STATS",
}

def nope(msg: str) -> discord.Embed:
    return notice(color=COLOR["crimson"], title="Không đủ quyền", body=msg)

def bad(msg: str) -> discord.Embed:
    return notice(color=COLOR["crimson"], title="Không được", body=msg)

def done(title: str, body: str = None, footer: str = None) -> discord.Embed:
    return notice(color=COLOR["mint"], title=title, body=body, footer=footer)

# =========================================================================
# LỆNH FATHER
# =========================================================================

async def handle_father(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Chỉ dùng trong server.", ephemeral=True)
        return

    auth = await authority_of(interaction.guild, interaction.user.id)
    if not auth["isFather"]:
        msg = "Lệnh này chỉ dành cho Father. Bạn là Cupid — dùng `/cupid`." if auth["rank"] == "cupid" else "Lệnh này chỉ dành cho Father. Chủ server luôn là Father và có thể phong cho bạn."
        await interaction.response.send_message(embed=nope(msg), ephemeral=True)
        return

    # Lấy subcommand (discord.py không có getSubcommand trực tiếp như discord.js, cần định nghĩa trong Command Tree)
    # Giả sử hàm này được gọi từ các subcommand function riêng rẽ.

async def father_reset_swipes(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    res = await reset_user_swipes(interaction.guild.id, user.id)
    
    embed = notice(
        color=COLOR["mint"],
        title="Đã reset",
        body=f"<@{user.id}> — xoá **{res['swipes']}** lượt lướt và **{res['matches']}** match.",
        footer="Họ và những người liên quan sẽ khám phá lại nhau từ đầu. Thread match cũ (nếu có) không bị xoá — dọn tay nếu cần."
    )
    await interaction.followup.send(embed=embed)

async def handle_cupid_form(interaction: discord.Interaction, user: discord.User, remove: bool = False):
    if not interaction.guild:
        await interaction.response.send_message("Chỉ dùng trong server.", ephemeral=True)
        return

    auth = await authority_of(interaction.guild, interaction.user.id)
    if not auth["isFather"]:
        await interaction.response.send_message(embed=nope("Lệnh này chỉ dành cho Father."), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    if remove:
        res = await set_cupid_permissions(interaction.guild, user.id, [], interaction.user.id)
        if not res["ok"]:
            await interaction.followup.send(embed=bad(res["error"]))
            return
        await interaction.followup.send(embed=done("Đã gỡ quyền", f"<@{user.id}> không còn quyền Cupid nào."))
        return

    res = await make_full_cupid(interaction.guild, user.id, interaction.user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return

    await interaction.followup.send(embed=done(
        "Đã cấp toàn quyền Cupid",
        f"<@{user.id}> giờ dùng được mọi lệnh /cupid: cấp Super Like, xử lý báo cáo, cấm hồ sơ, xem số liệu.",
        "Muốn cấp từng quyền lẻ thì dùng /father cupid. Gỡ: /cupidform remove:true."
    ))

    try:
        await user.send(embed=notice(
            color=COLOR["mint"],
            title=f"{GLYPH['sparkle']} Bạn được cấp quyền Cupid",
            body=f"Ở **{interaction.guild.name}**. Dùng /cupid để xem các lệnh quản trị."
        ))
    except discord.Forbidden:
        pass

async def father_setup(interaction: discord.Interaction, verified_role: discord.Role, lounge: discord.TextChannel, mod_channel: discord.TextChannel, daily_swipes: int = 15):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    problems = []

    if verified_role.id == guild.id:
        problems.append("Không thể dùng `@everyone` làm role xác minh — như vậy là không có lớp bảo vệ nào.")

    me = guild.me
    auto_configured = True
    
    try:
        # Cấp quyền cho Lounge Channel
        lounge_overwrite = lounge.overwrites_for(me)
        lounge_overwrite.update(
            read_messages=True, 
            send_messages=True, 
            send_messages_in_threads=True, 
            create_private_threads=True, 
            manage_threads=True
        )
        await lounge.set_permissions(me, overwrite=lounge_overwrite)
        
        # Cấp quyền cho Mod Channel
        mod_overwrite = mod_channel.overwrites_for(me)
        mod_overwrite.update(read_messages=True, send_messages=True)
        await mod_channel.set_permissions(me, overwrite=mod_overwrite)
    except Exception:
        auto_configured = False

    lounge_perms = lounge.permissions_for(me)
    if not lounge_perms.read_messages: problems.append(f"Bot không **nhìn thấy** <#{lounge.id}> (thiếu View Channel).")
    if not lounge_perms.create_private_threads: problems.append(f"Bot thiếu quyền **Create Private Threads** ở <#{lounge.id}>.")
    if not lounge_perms.send_messages_in_threads: problems.append(f"Bot thiếu quyền **Send Messages in Threads** ở <#{lounge.id}>.")
    if not lounge_perms.manage_threads: problems.append(f"Bot thiếu quyền **Manage Threads** ở <#{lounge.id}> (cần để dọn phòng cũ).")

    mod_perms = mod_channel.permissions_for(me)
    if not mod_perms.read_messages: problems.append(f"Bot không **nhìn thấy** <#{mod_channel.id}> — báo cáo sẽ không gửi được (lỗi Missing Access).")
    if not mod_perms.send_messages: problems.append(f"Bot không gửi được tin nhắn vào <#{mod_channel.id}>.")

    if problems and not auto_configured:
        problems.append("_Bot không tự cấu hình được 2 kênh (thiếu Manage Roles). Cấp cho bot quyền Manage Roles rồi chạy lại, hoặc tự thêm bot vào 2 kênh._")

    if mod_channel.permissions_for(guild.default_role).read_messages:
        problems.append(f"<#{mod_channel.id}> đang cho @everyone xem được. Báo cáo chứa thông tin nhạy cảm — hãy dùng kênh riêng của mod.")

    if problems:
        embed = notice(
            color=COLOR["crimson"],
            title="Chưa bật được",
            body="\n".join([f"• {p}" for p in problems]),
            footer="Sửa xong rồi chạy lại lệnh này."
        )
        await interaction.followup.send(embed=embed)
        return

    # Lưu Database (Giả định db.guild_config là collection)
    await db.guild_configs.update_one(
        {"_id": str(guild.id)},
        {"$set": {
            "guildId": str(guild.id),
            "enabled": True,
            "verifiedRoleId": str(verified_role.id),
            "loungeChannelId": str(lounge.id),
            "modChannelId": str(mod_channel.id),
            "dailySwipeLimit": daily_swipes
        }},
        upsert=True
    )

    embed = notice(
        color=COLOR["mint"],
        title=f"{GLYPH['sparkle']} Đã bật",
        body=f"**Role xác minh:** <@&{verified_role.id}>\n**Phòng match:** <#{lounge.id}>\n**Kênh báo cáo:** <#{mod_channel.id}>\n**Trần lướt/ngày:** {daily_swipes} (tự co giãn theo số người trong server)",
        footer=f"Chỉ người có {verified_role.name} dùng được bot. Việc xác minh 18+ và cấp role là trách nhiệm của bạn — bot không tự xác minh tuổi được.\nCấp quyền cho mod bằng /father cupid."
    )
    await interaction.followup.send(embed=embed)

async def father_promote(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    res = await promote_father(interaction.guild, user.id, interaction.user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return
    await interaction.followup.send(embed=done("Đã phong Father", f"<@{user.id}> giờ có **toàn quyền**: sửa cấu hình, phong Father khác, cấp quyền Cupid.", "Father không tự gỡ quyền của mình được — phải nhờ một Father khác."))

async def father_demote(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    res = await demote_father(interaction.guild, user.id, interaction.user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return
    await interaction.followup.send(embed=done("Đã gỡ quyền Father", f"<@{user.id}> không còn quyền quản trị nào."))

async def father_cupid_picker(interaction: discord.Interaction, user: discord.User):
    guild = interaction.guild
    auth = await authority_of(guild, user.id)
    
    if auth["rank"] == "owner":
        await interaction.response.send_message(embed=bad("Chủ server đã có toàn quyền."), ephemeral=True)
        return
    if auth["rank"] == "father":
        await interaction.response.send_message(embed=bad("Người này là Father — đã có toàn quyền sẵn."), ephemeral=True)
        return
    if user.bot:
        await interaction.response.send_message(embed=bad("Không thể cấp quyền cho bot."), ephemeral=True)
        return

    current = set(auth["permissions"])
    
    options = []
    for p in ALL_PERMISSIONS:
        options.append(discord.SelectOption(
            label=PERMISSION_LABEL[p],
            description=PERMISSION_HINT[p][:100],
            value=p,
            default=(p in current)
        ))

    select = discord.ui.Select(
        custom_id=f"cp|{user.id}", # Custom ID đơn giản hóa, cần tích hợp ID lib thực tế
        placeholder="Chọn quyền",
        min_values=0,
        max_values=len(ALL_PERMISSIONS),
        options=options
    )
    
    view = discord.ui.View()
    view.add_item(select)
    
    desc = f"### Quyền Cupid cho {user.name}\n"
    desc += f"Đang có **{len(current)}** quyền. Chọn lại để thay đổi." if current else "Người này chưa có quyền nào. Chọn những quyền muốn cấp."
    desc += f"\n{sub('Bỏ chọn hết rồi lưu = thu hồi toàn bộ quyền Cupid.')}"
    
    embed = discord.Embed(description=desc, color=COLOR["rose"])
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Hàm xử lý callback của menu chọn quyền Cupid
async def handle_cupid_perms_select(interaction: discord.Interaction, target_id: str, values: list):
    if not interaction.guild: return
    
    auth = await authority_of(interaction.guild, interaction.user.id)
    if not auth["isFather"]:
        await interaction.response.send_message(embed=nope("Chỉ Father cấp được quyền Cupid."), ephemeral=True)
        return

    perms = [v for v in values if v in ALL_PERMISSIONS]
    res = await set_cupid_permissions(interaction.guild, target_id, perms, interaction.user.id)
    
    if not res["ok"]:
        await interaction.response.send_message(embed=bad(res["error"]), ephemeral=True)
        return

    body = f"<@{target_id}> giờ có thể:\n" + "\n".join([f"• {PERMISSION_LABEL[p]}" for p in perms]) if perms else f"<@{target_id}> không còn quyền quản trị nào."
    
    embed = notice(
        color=COLOR["mint"] if perms else COLOR["slate"],
        title="Đã cấp quyền Cupid" if perms else "Đã thu hồi quyền Cupid",
        body=body,
        footer="Họ dùng /cupid để thao tác." if perms else None
    )
    await interaction.response.edit_message(embed=embed, view=None)

async def father_staff(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    staff_data = await list_staff(interaction.guild)
    
    owner_id = staff_data["ownerId"]
    fathers = staff_data["fathers"]
    cupids = staff_data["cupids"]

    lines = [f"**Chủ server** — toàn quyền, không gỡ được\n<@{owner_id}>\n"]
    
    lines.append(f"**Father** — toàn quyền ({len(fathers)})")
    lines.append("  ".join([f"<@{f['userId']}>" for f in fathers]) if fathers else "_chưa có ai_")
    lines.append("")
    
    lines.append(f"**Cupid** — quyền được cấp ({len(cupids)})")
    if cupids:
        for c in cupids:
            perms_str = ", ".join([PERMISSION_LABEL[p] for p in c["permissions"]])
            lines.append(f"<@{c['userId']}> — {perms_str}")
    else:
        lines.append("_chưa có ai_")

    embed = notice(
        color=COLOR["slate"],
        title="Nhân sự",
        body="\n".join(lines)[:3800],
        footer="Cấp quyền: /father cupid  ·  Phong Father: /father promote"
    )
    await interaction.followup.send(embed=embed)

async def father_audit(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    
    recent = await recent_grants(guild_id, 15)
    by_staff = await grants_by_staff(guild_id, 30)

    if not recent:
        await interaction.followup.send(embed=notice(color=COLOR["slate"], title="Chưa có ai cấp Super Like", footer="Cấp bằng /cupid give."))
        return

    staff_lines = [f"<@{s['_id']}> — **{s['total_amount']}** qua {s['grant_count']} lần" for s in by_staff]
    
    recent_lines = []
    for g in recent:
        ts = int(g['createdAt'].timestamp())
        amt = f"+{g['amount']}" if g['amount'] > 0 else str(g['amount'])
        reason = f" — {g['reason']}" if g.get('reason') else ""
        recent_lines.append(f"<t:{ts}:R> · <@{g['byUserId']}> → <@{g['toUserId']}> **{amt}**{reason}")

    body = f"**Theo người cấp (30 ngày qua)**\n" + "\n".join(staff_lines) + "\n\n**Gần đây**\n" + "\n".join(recent_lines)
    
    embed = notice(
        color=COLOR["slate"],
        title="Nhật ký cấp Super Like",
        body=body[:3800],
        footer="Super Like được tạo ra từ hư không bởi một con người. Đây là cách duy nhất phát hiện một Cupid đang cấp quá tay."
    )
    await interaction.followup.send(embed=embed)

# =========================================================================
# LỆNH CUPID
# =========================================================================

async def handle_cupid(interaction: discord.Interaction, subcommand: str, **kwargs):
    if not interaction.guild:
        await interaction.response.send_message("Chỉ dùng trong server.", ephemeral=True)
        return

    need = CUPID_REQUIRED.get(subcommand)
    if not need: return

    auth = await authority_of(interaction.guild, interaction.user.id)
    if need not in auth["permissions"]:
        msg = "Bạn không có quyền quản trị. Nhờ Father cấp bằng `/father cupid`." if auth["rank"] == "none" else f"Bạn là {RANK_LABEL[auth['rank']]} nhưng chưa được cấp quyền **{PERMISSION_LABEL[need]}**."
        await interaction.response.send_message(embed=nope(msg), ephemeral=True)
        return

    # Routing
    if subcommand == "give": await cupid_give(interaction, **kwargs)
    elif subcommand == "balance": await cupid_balance(interaction, **kwargs)
    elif subcommand == "reports": await cupid_reports(interaction)
    elif subcommand == "resolve": await cupid_resolve(interaction, **kwargs)
    elif subcommand == "ban": await cupid_ban(interaction, **kwargs)
    elif subcommand == "unban": await cupid_unban(interaction, **kwargs)
    elif subcommand == "status": await cupid_status(interaction)

async def cupid_give(interaction: discord.Interaction, user: discord.User, amount: int, reason: str = None):
    await interaction.response.defer(ephemeral=True)
    
    if user.bot:
        await interaction.followup.send(embed=bad("Không thể cấp cho bot."))
        return

    res = await give_superlikes(interaction.guild.id, interaction.user.id, user.id, amount, reason)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return

    title_action = f"{GLYPH['superLike']} Đã cấp {res['delta']} Super Like" if res['delta'] > 0 else f"Đã thu hồi {-res['delta']}"
    await interaction.followup.send(embed=done(title_action, f"<@{user.id}> — số dư giờ là **{res['balance']}**.", "Đã ghi vào nhật ký. Father xem được bằng /father audit."))

    if res['delta'] > 0:
        try:
            body_text = f"> {reason}" if reason else None
            await user.send(embed=notice(
                color=COLOR["violet"],
                title=f"{GLYPH['superLike']} Bạn nhận được {res['delta']} Super Like",
                body=body_text,
                footer=f"Từ {interaction.guild.name} {GLYPH['dot']} số dư: {res['balance']}. Dùng khi lướt bằng /explore."
            ))
        except discord.Forbidden:
            pass

async def cupid_balance(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    balance = await get_balance(interaction.guild.id, user.id)
    
    # Lấy 5 lần cấp gần nhất
    granted = await db.sl_grants.find({"guildId": str(interaction.guild.id), "toUserId": str(user.id)}).sort("createdAt", -1).limit(5).to_list(length=5)
    
    lines = []
    for g in granted:
        ts = int(g['createdAt'].timestamp())
        amt = f"+{g['amount']}" if g['amount'] > 0 else str(g['amount'])
        reason = f" — {g['reason']}" if g.get('reason') else ""
        lines.append(f"<t:{ts}:R> · <@{g['byUserId']}> **{amt}**{reason}")

    body = "**Gần đây**\n" + "\n".join(lines) if lines else "_Chưa từng được cấp lần nào._"
    
    embed = notice(
        color=COLOR["violet"],
        title=f"{user.name} có {balance} Super Like",
        body=body
    )
    await interaction.followup.send(embed=embed)

async def cupid_reports(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    open_reps = await open_reports(interaction.guild.id, 10)

    if not open_reps:
        await interaction.followup.send(embed=notice(color=COLOR["mint"], title="Không có báo cáo nào đang mở", footer="Yên bình."))
        return

    by_target = {}
    for r in open_reps:
        target_id = r["reportedId"]
        if target_id not in by_target: by_target[target_id] = []
        by_target[target_id].append(r)

    lines = []
    for user_id, rs in by_target.items():
        snap = rs[0].get("snapshot", {})
        lines.append(f"**<@{user_id}>** — {snap.get('displayName', '?')}, {snap.get('age', '?')}  {GLYPH['dot']}  **{len(rs)}** báo cáo")
        
        for r in rs:
            r_label = reason_label(r['reason'])
            details = f"\n    _{r['details'][:120]}_" if r.get('details') else ""
            lines.append(f"  {GLYPH['dot']} {r_label} — <@{r['reporterId']}>{details}")
        lines.append("")

    embed = notice(
        color=COLOR["crimson"],
        title=f"{GLYPH['report']} {len(open_reps)} báo cáo đang mở",
        body="\n".join(lines)[:3800],
        footer="Đóng bằng /cupid resolve. Chọn 'không có cơ sở' sẽ bỏ ẩn hồ sơ — hồ sơ bị ẩn sẽ nằm ẩn mãi nếu không ai đóng báo cáo."
    )
    await interaction.followup.send(embed=embed)

async def cupid_resolve(interaction: discord.Interaction, user: discord.User, action: str):
    await interaction.response.defer(ephemeral=True)
    res = await resolve_reports(interaction.guild.id, user.id, action, interaction.user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return
    await interaction.followup.send(embed=done("Đã xử lý", f"<@{user.id}> — {res.get('note', '')}"))

async def cupid_ban(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    res = await ban_profile(interaction.guild.id, user.id, interaction.user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return
    await interaction.followup.send(embed=notice(
        color=COLOR["crimson"],
        title="Đã cấm hồ sơ",
        body=f"<@{user.id}> — {res.get('note', '')}",
        footer="Họ không tự bỏ cấm được. Bỏ cấm bằng /cupid unban."
    ))

async def cupid_unban(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    res = await unban_profile(interaction.guild.id, user.id)
    if not res["ok"]:
        await interaction.followup.send(embed=bad(res["error"]))
        return
    await interaction.followup.send(embed=done("Đã bỏ cấm", f"<@{user.id}> — {res.get('note', '')}"))

async def cupid_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)
    cfg = await get_guild_config(guild_id)
    
    if not cfg or not cfg.get("enabled"):
        await interaction.followup.send(embed=notice(color=COLOR["slate"], title="Bot chưa được bật", footer="Father chạy /father setup."))
        return

    # Tính toán thông kê (Thay thế bằng các count từ MongoDB)
    active = await db.profiles.count_documents({"guildId": guild_id, "status": "ACTIVE"})
    draft = await db.profiles.count_documents({"guildId": guild_id, "status": "DRAFT"})
    review = await db.profiles.count_documents({"guildId": guild_id, "status": "UNDER_REVIEW"})
    banned = await db.profiles.count_documents({"guildId": guild_id, "status": "BANNED"})
    open_r = await db.reports.count_documents({"guildId": guild_id, "status": "OPEN"})
    matches = await db.matches.count_documents({"guildId": guild_id})
    
    # Lượt quẹt 24h qua
    import datetime
    since_24h = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    swipes_24h = await db.swipes.count_documents({"guildId": guild_id, "createdAt": {"$gte": since_24h}})
    
    # Tổng Like/Pass
    likes_count = await db.swipes.count_documents({"guildId": guild_id, "action": "LIKE"})
    passes_count = await db.swipes.count_documents({"guildId": guild_id, "action": "PASS"})
    
    # Tổng SL
    pipeline = [{"$match": {"guildId": guild_id}}, {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    sl_res = await db.sl_balances.aggregate(pipeline).to_list(length=1)
    supers = sl_res[0]["total"] if sl_res else 0

    total_swipes = likes_count + passes_count
    like_ratio = round((likes_count / total_swipes) * 100) if total_swipes > 0 else 0

    needs_attention = review > 0 or open_r > 0

    lines = [
        f"**Hồ sơ hoạt động:** {active}",
        f"**Hồ sơ chưa xong:** {draft}",
        f"**Chờ xem xét:** {review}{'  ⚠' if review > 0 else ''}",
        f"**Bị cấm:** {banned}",
        f"**Báo cáo đang mở:** {open_r}{'  ⚠' if open_r > 0 else ''}",
        f"**Tổng match:** {matches}",
        f"**Tỷ lệ thích:** {like_ratio}% ({likes_count} thích / {passes_count} bỏ qua)",
        f"**Lượt lướt 24h qua:** {swipes_24h}",
        f"**Super Like đang lưu hành:** {supers}",
        "",
        f"**Role xác minh:** <@&{cfg.get('verifiedRoleId')}>",
        f"**Phòng match:** <#{cfg.get('loungeChannelId')}>",
        f"**Kênh báo cáo:** <#{cfg.get('modChannelId')}>",
        f"**Trần lướt/ngày:** {cfg.get('dailySwipeLimit')}"
    ]

    # Giả định LIMITS.minDailySwipes = 5
    footer_text = f"Dưới 20 hồ sơ thì trần lướt tự hạ xuống mức tối thiểu (5/ngày) — không đủ người để lướt." if active < 20 else None

    embed = notice(
        color=COLOR["crimson"] if needs_attention else COLOR["slate"],
        title="Tình trạng",
        body="\n".join(lines),
        footer=footer_text
    )
    await interaction.followup.send(embed=embed)
