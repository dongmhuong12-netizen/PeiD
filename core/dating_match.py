import datetime
import logging
import discord
from core.dating_storage import db, get_profile, get_guild_config
from core.dating_dm import send_dm
from core.dating_glyphs import get_glyph_config, get_glyph_sync
from ui.dating_profile_card import notice, match_reveal_card
from ui.dating_theme import COLOR, GLYPH, sub

# Collections
matches_col = db.matches
sl_sent_col = db.superlikes_sent

log = logging.getLogger("dating.match")
OPT_IN_HOURS = 24
IDLE_THREAD_HOURS = 72
MAX_ACTIVE_MATCHES = 5

def partner_of(m: dict, me_id: str) -> str:
    """Xác định ID của đối phương trong 1 Match"""
    return m["userBId"] if m["userAId"] == me_id else m["userAId"]

async def pending_for(guild_id: str, user_id: str) -> list:
    """Lấy danh sách Match đang chờ user phản hồi"""
    now = datetime.datetime.now(datetime.timezone.utc)
    cursor = matches_col.find({
        "guildId": str(guild_id),
        "status": "PENDING_OPT_IN",
        "optInExpiresAt": {"$gt": now},
        "$or": [{"userAId": str(user_id)}, {"userBId": str(user_id)}]
    }).sort("createdAt", -1).limit(10)
    return await cursor.to_list(length=10)

async def active_for(guild_id: str, user_id: str) -> list:
    """Lấy danh sách Phòng Chat đang hoạt động"""
    cursor = matches_col.find({
        "guildId": str(guild_id),
        "status": "ACTIVE",
        "$or": [{"userAId": str(user_id)}, {"userBId": str(user_id)}]
    }).sort("lastActivityAt", -1).limit(5)
    return await cursor.to_list(length=5)

async def count_active_matches(guild_id: str, user_id: str) -> int:
    return await matches_col.count_documents({
        "guildId": str(guild_id),
        "status": "ACTIVE",
        "$or": [{"userAId": str(user_id)}, {"userBId": str(user_id)}]
    })

async def announce_match(bot: discord.Client, match_id: str):
    """Gửi thông báo có Match mới (Qua tin nhắn riêng DM)"""
    match = await matches_col.find_one({"_id": match_id})
    if not match or match.get("status") != "PENDING_OPT_IN":
        return

    guild_id = match["guildId"]
    user_a = match["userAId"]
    user_b = match["userBId"]

    await _dm_opt_in(bot, match_id, guild_id, user_a, user_b)
    await _dm_opt_in(bot, match_id, guild_id, user_b, user_a)

async def _dm_opt_in(bot: discord.Client, match_id: str, guild_id: str, me_id: str, them_id: str):
    them = await get_profile(guild_id, them_id)
    if not them: return

    # Lấy lời nhắn Super Like (Nếu có)
    their_super_like = await sl_sent_col.find_one({"_id": f"{guild_id}_{them_id}_{me_id}"})
    note = their_super_like.get("note") if their_super_like else None

    guild = bot.get_guild(int(guild_id))
    guild_name = guild.name if guild else "Server"

    glyph_cfg = await get_glyph_config(guild_id)
    gp_sparkle = get_glyph_sync(glyph_cfg, "sparkle")
    gp_superlike = get_glyph_sync(glyph_cfg, "superLike")
    gp_chat = get_glyph_sync(glyph_cfg, "chat")

    body_text = f"**{them.get('displayName')}** cũng thích bạn.\n"
    if note:
        body_text += f"> {note}\n-# {gp_superlike} gửi kèm Super Like\n"

    footer_text = f"Cả hai cùng bấm 'Bắt đầu chat' thì bot mới mở phòng riêng. Không ai bị kéo vào đâu cả.\nLời mời hết hạn sau {OPT_IN_HOURS} giờ. {GLYPH['dot']} {guild_name}"

    view = discord.ui.View()
    view.add_item(discord.ui.Button(custom_id=f"mr|{match_id}", label="Bắt đầu chat", emoji=gp_chat, style=discord.ButtonStyle.success))
    view.add_item(discord.ui.Button(custom_id=f"md|{match_id}", label="Thôi, bỏ qua", style=discord.ButtonStyle.secondary))

    embed = notice(color=COLOR["gold"], title=f"{gp_sparkle} Match!", body=body_text, footer=footer_text)

    try:
        user = await bot.fetch_user(int(me_id))
        await send_dm(user, embed=embed, view=view)
    except Exception as e:
        log.debug(f"Không gửi được DM cho {me_id}: {e}")

async def decline_match(match_id: str, user_id: str) -> bool:
    res = await matches_col.update_one(
        {
            "_id": match_id, 
            "status": "PENDING_OPT_IN", 
            "$or": [{"userAId": str(user_id)}, {"userBId": str(user_id)}]
        },
        {"$set": {"status": "EXPIRED", "unmatchedBy": str(user_id)}}
    )
    return res.modified_count > 0

async def mark_ready(bot: discord.Client, match_id: str, user_id: str) -> dict:
    """Xác nhận người dùng đã sẵn sàng Chat. Nếu cả 2 cùng OK -> Mở Thread."""
    match = await matches_col.find_one({"_id": match_id})
    if not match: return {"kind": "gone"}
    
    if match.get("status") == "ACTIVE" and match.get("threadId"):
        return {"kind": "opened", "threadId": match["threadId"]}
        
    if match.get("status") != "PENDING_OPT_IN": return {"kind": "gone"}

    now = datetime.datetime.now(datetime.timezone.utc)
    # Vì dữ liệu trong DB trả về datetime dạng naive đôi khi, ta cần format để so sánh
    if match.get("optInExpiresAt") and match["optInExpiresAt"].replace(tzinfo=datetime.timezone.utc) < now:
        return {"kind": "expired"}

    user_id = str(user_id)
    is_a = (match["userAId"] == user_id)
    if not is_a and match["userBId"] != user_id: return {"kind": "gone"}

    # Kiểm tra giới hạn 5 phòng
    active_count = await count_active_matches(match["guildId"], user_id)
    if active_count >= MAX_ACTIVE_MATCHES:
        return {"kind": "full"}

    # Đánh dấu Sẵn Sàng (Atomic Update)
    await matches_col.update_one(
        {"_id": match_id, "status": "PENDING_OPT_IN"},
        {"$set": {"userAReady": True} if is_a else {"userBReady": True}}
    )

    # Đọc lại trạng thái mới nhất
    fresh = await matches_col.find_one({"_id": match_id})
    if not fresh or fresh.get("status") != "PENDING_OPT_IN": return {"kind": "gone"}
    
    # Chưa đủ 2 người OK
    if not (fresh.get("userAReady") and fresh.get("userBReady")): 
        return {"kind": "waiting"}

    # Đủ 2 người -> Khai trương Phòng Chat
    thread_id = await _open_thread(bot, match_id)
    return {"kind": "opened", "threadId": thread_id} if thread_id else {"kind": "gone"}

async def _open_thread(bot: discord.Client, match_id: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Khoá atomic để chống 2 thread sinh ra cùng lúc
    claimed = await matches_col.update_one(
        {"_id": match_id, "status": "PENDING_OPT_IN", "threadId": None},
        {"$set": {"status": "ACTIVE", "lastActivityAt": now}}
    )
    
    if claimed.modified_count == 0:
        existing = await matches_col.find_one({"_id": match_id})
        return existing.get("threadId") if existing else None

    match = await matches_col.find_one({"_id": match_id})
    guild_id = match["guildId"]
    
    cfg = await get_guild_config(guild_id)
    if not cfg or not cfg.get("loungeChannelId"):
        log.error(f"Guild {guild_id} chưa cấu hình Lounge Channel.")
        await matches_col.update_one({"_id": match_id}, {"$set": {"status": "PENDING_OPT_IN"}})
        return None

    a = await get_profile(guild_id, match["userAId"])
    b = await get_profile(guild_id, match["userBId"])
    if not a or not b: return None

    try:
        channel = await bot.fetch_channel(int(cfg["loungeChannelId"]))
        
        # Tạo Private Thread bằng discord.py
        thread = await channel.create_thread(
            name=f"{a['displayName']} & {b['displayName']}",
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=4320, # 3 ngày
            reason=f"Match Dating: {match_id}"
        )

        await matches_col.update_one({"_id": match_id}, {"$set": {"threadId": str(thread.id)}})

        # Mời 2 người vào phòng
        await thread.add_user(await bot.fetch_user(int(match["userAId"])))
        await thread.add_user(await bot.fetch_user(int(match["userBId"])))

        glyphs = await get_glyph_config(guild_id)

        # Gửi Card Profile của nhau vào phòng
        card_b_embed, card_b_view = match_reveal_card(b, b.get('photoUrl'), match_id, glyphs)
        await thread.send(content=f"<@{match['userAId']}> <@{match['userBId']}>", embed=card_b_embed, view=card_b_view)
        
        card_a_embed, card_a_view = match_reveal_card(a, a.get('photoUrl'), match_id, glyphs)
        await thread.send(embed=card_a_embed, view=card_a_view)
        
        await thread.send(content=sub(f"Phòng này chỉ có hai bạn. Im lặng quá {IDLE_THREAD_HOURS} giờ thì bot sẽ tự dọn."))

        # Khởi động Quiz
        quiz_view = discord.ui.View()
        quiz_view.add_item(discord.ui.Button(custom_id=f"qst|{match_id}", label="Chơi Quiz 🎮", style=discord.ButtonStyle.primary))
        await thread.send(embed=notice(
            color=COLOR["violet"],
            title="🎮 Minigame: Trắc nghiệm Ăn ý",
            body="Để xua tan không khí ngại ngùng lúc đầu, hai bạn hãy thử chơi trò chơi trắc nghiệm 5 câu hỏi xem ăn ý tới mức nào nhé!"
        ), view=quiz_view)

        return str(thread.id)

    except Exception as e:
        log.error(f"Tạo thread thất bại cho match {match_id}: {e}")
        await matches_col.update_one({"_id": match_id}, {"$set": {"status": "PENDING_OPT_IN"}})
        return None

async def unmatch(bot: discord.Client, match_id: str, by_user_id: str) -> bool:
    """Chia tay hoàng hôn! Xóa Match và Khóa Thread"""
    match = await matches_col.find_one({"_id": match_id})
    if not match: return False
    
    by_user_id = str(by_user_id)
    if match["userAId"] != by_user_id and match["userBId"] != by_user_id: return False
    if match.get("status") == "UNMATCHED": return False

    await matches_col.update_one(
        {"_id": match_id},
        {"$set": {"status": "UNMATCHED", "unmatchedBy": by_user_id}}
    )

    other_id = match["userBId"] if match["userAId"] == by_user_id else match["userAId"]

    # Khoá Thread
    if match.get("threadId"):
        try:
            thread = await bot.fetch_channel(int(match["threadId"]))
            if isinstance(thread, discord.Thread):
                await thread.send(embed=notice(color=COLOR["slate"], title="Match đã kết thúc", footer="Phòng này sẽ được khoá."))
                await thread.edit(locked=True, archived=True, reason=f"Unmatch bởi {by_user_id}")
        except Exception as e:
            log.debug(f"Không đóng được thread {match.get('threadId')}: {e}")

    # Nhắn DM cho người bị unmatch để báo nhẹ nhàng
    try:
        user = await bot.fetch_user(int(other_id))
        await send_dm(user, embed=notice(
            color=COLOR["slate"],
            title="Một match đã kết thúc",
            body="Không sao cả — chuyện này bình thường.",
            footer="Dùng /explore để tiếp tục."
        ))
    except Exception:
        pass

    return True

