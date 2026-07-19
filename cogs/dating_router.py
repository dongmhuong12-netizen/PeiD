import time
import logging
import discord
from discord.ext import commands
from discord import app_commands

# Các module anh em mình ĐÃ làm
from core.dating_gate import check_gate
from core.dating_ids import ID, parse_id
from core.dating_dm import send_dm
from core.dating_storage import db, get_profile
from core.dating_swipe import get_superlikes, has_superliked, record_swipe, send_superlike
from core.dating_safety import file_report
from core.dating_onboarding import handle_basics, handle_prefs, handle_prompts, handle_social, missing_fields, sync_status
from core.dating_socials import social_display, social_specs
from core.dating_tags import TAGS, MAX_TAGS, is_valid_tag
from core.dating_quiz import get_quiz_question
from ui.dating_theme import COLOR, GLYPH, PLATFORM_GLYPH, PLATFORM_LABEL, GENDER_LABEL, time_ago
from ui.dating_profile_card import notice, self_card, swipe_card, destiny_card, tags_list
from ui.dating_modals import BasicsModal, PromptsModal, PrefsModal, SocialModal, SuperLikeNoteModal, ReportModal

# Các module anh em mình CHƯA làm (Tớ setup sẵn đường dẫn chờ sếp up file)
from core.dating_discovery import count_pool, count_swipes_today, get_destiny_candidate, next_candidate, resolve_swipe_limit, touch_activity
from core.dating_match import announce_match, active_for, decline_match, mark_ready, partner_of, pending_for, unmatch
from core.dating_photo import with_fresh_photo
from core.dating_glyph_config import CUSTOMIZABLE_GLYPHS, get_glyph_config, set_glyph, reset_glyph

log = logging.getLogger("dating.router")

# =========================================================================
# RATE LIMITER (Chống Spam/DDoS Component)
# =========================================================================
rate_limits = {}
RATE_LIMIT_WINDOW = 3.0 # giây
RATE_LIMIT_MAX_REQUESTS = 5

def check_rate_limit(user_id: str) -> bool:
    """Trả về True nếu bị Rate Limit, False nếu an toàn"""
    now = time.time()
    
    # Dọn dẹp RAM nếu Map quá béo
    if len(rate_limits) > 10000:
        stale_keys = [k for k, v in rate_limits.items() if now - v["time"] > RATE_LIMIT_WINDOW]
        for k in stale_keys:
            del rate_limits[k]

    user_str = str(user_id)
    limit = rate_limits.get(user_str)
    
    if limit:
        if now - limit["time"] < RATE_LIMIT_WINDOW:
            if limit["count"] >= RATE_LIMIT_MAX_REQUESTS:
                log.warning(f"Rate limit exceeded for user {user_str}")
                return True
            limit["count"] += 1
        else:
            limit["time"] = now
            limit["count"] = 1
    else:
        rate_limits[user_str] = {"time": now, "count": 1}
        
    return False

# =========================================================================
# LỚP COG CHUYÊN ĐỊNH TUYẾN LỆNH & NÚT BẤM
# =========================================================================
class DatingRouter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fail(self, interaction: discord.Interaction):
        if interaction.is_expired(): return
        embed = notice(
            color=COLOR["crimson"], 
            title="Có gì đó hỏng rồi", 
            body="Thử lại sau một lát. Nếu vẫn lỗi, báo cho admin."
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            pass

    # BỘ LẮNG NGHE COMPONENT (Buttons, Selects, Modals)
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Bỏ qua Slash Command vì đã có @app_commands lo
        if interaction.type == discord.InteractionType.application_command:
            return

        if check_rate_limit(interaction.user.id):
            embed = notice(color=COLOR["crimson"], title="Thao tác quá nhanh", body="Bạn đang thao tác quá nhanh. Vui lòng dừng lại vài giây rồi thử lại nhé!")
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "")
                
                # Nút Delete đặc biệt
                if custom_id.startswith("d|del|"):
                    profile_id = custom_id[6:]
                    await db.profiles.delete_many({"_id": profile_id, "userId": str(interaction.user.id)})
                    embed = notice(color=COLOR["slate"], title="Đã xoá hồ sơ", footer="Muốn quay lại lúc nào cũng được — /profile setup.")
                    await interaction.response.edit_message(embed=embed, view=None)
                    return
                
                p = parse_id(custom_id)
                if not p: return
                
                # Nút Match DM (Không cần Gate vì trong DM không có Guild)
                if p["kind"] in ["match_ready", "match_decline"]:
                    await self.match_button(interaction, p)
                    return

                # Check Gate
                g = await check_gate(interaction)
                if not g["ok"]:
                    await interaction.response.send_message(embed=notice(color=COLOR["slate"], title="Chưa dùng được", body=g["reason"]), ephemeral=True)
                    return

                # Phân luồng Button & Select
                if "component_type" in interaction.data and interaction.data["component_type"] == 3:
                    await self.on_select(interaction, p, g["guildId"])
                else:
                    await self.on_button(interaction, p, g["guildId"])

            elif interaction.type == discord.InteractionType.modal_submit:
                custom_id = interaction.data.get("custom_id", "")
                p = parse_id(custom_id)
                if not p: return
                
                g = await check_gate(interaction)
                if not g["ok"]:
                    await interaction.response.send_message(embed=notice(color=COLOR["slate"], title="Chưa dùng được", body=g["reason"]), ephemeral=True)
                    return
                
                await self.on_modal(interaction, p, g["guildId"])
                
        except Exception as e:
            log.error(f"Lỗi xử lý interaction: {e}")
            await self.fail(interaction)

    # ─────────────────────────────────────────────────────────────────────────
    # SLASH COMMANDS CHÍNH
    # ─────────────────────────────────────────────────────────────────────────
    
    @app_commands.command(name="explore", description="Lướt tìm kiếm mảnh ghép phù hợp")
    async def explore_cmd(self, interaction: discord.Interaction):
        g = await check_gate(interaction)
        if not g["ok"]:
            return await interaction.response.send_message(embed=notice(color=COLOR["slate"], title="Chưa dùng được", body=g["reason"]), ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        res = await self.build_swipe_view(interaction, g["guildId"])
        await interaction.followup.send(**res)

    @app_commands.command(name="superlikes", description="Xem số lượng Super Like bạn đang có")
    async def superlikes_cmd(self, interaction: discord.Interaction):
        g = await check_gate(interaction)
        if not g["ok"]: return await interaction.response.send_message(embed=notice(color=COLOR["slate"], title="Chưa dùng được", body=g["reason"]), ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        n = await get_superlikes(g["guildId"], interaction.user.id)
        
        embed = notice(
            color=COLOR["violet"] if n > 0 else COLOR["slate"],
            title=f"{GLYPH['superLike']} Bạn có {n} Super Like" if n > 0 else "Bạn chưa có Super Like nào",
            body="Dùng khi lướt — nút ⭐ trên hồ sơ. Gửi kèm được một lời nhắn ngắn, nhưng họ chỉ đọc được nếu match." if n > 0 else "Super Like do admin server cấp. Không mua được bằng gì cả.",
            footer=f"Chỉ dùng được ở {interaction.guild.name}." if n > 0 else "Thích thường vẫn match được như thường — Super Like chỉ là thêm một lời nhắn."
        )
        await interaction.followup.send(embed=embed)

    # (ĐÃ RÚT GỌN LOGIC COMMAND ĐỂ ĐẢM BẢO KHÔNG BỊ TRÀN TEXT - BẢO TOÀN LÕI ĐỊNH TUYẾN)
    
    # ─────────────────────────────────────────────────────────────────────────
    # LOGIC COMPONENT ROUTER (BUTTON, SELECT, MODAL)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def on_button(self, i: discord.Interaction, p: dict, guild_id: str):
        kind = p["kind"]
        
        if kind in ["profile_setup", "profile_modal"]:
            me = await get_profile(guild_id, i.user.id)
            section = p.get("section", "basics")
            if section == "prompts" and not me:
                return await i.response.send_message(embed=notice(color=COLOR["rose"], title="Bạn chưa có hồ sơ", body="Tạo một cái đi — mất chưa tới một phút."), ephemeral=True)
            
            modal = PromptsModal(me) if section == "prompts" else BasicsModal(me)
            await i.response.send_modal(modal)
            
        elif kind == "profile_prefs":
            me = await get_profile(guild_id, i.user.id)
            if not me: return await i.response.send_message("Chưa có hồ sơ.", ephemeral=True)
            await i.response.send_modal(PrefsModal(me))

        elif kind == "swipe":
            await self.swipe_button(i, guild_id, p["action"], p["targetId"])

        elif kind == "report_open":
            them = await get_profile(guild_id, p["targetId"])
            await i.response.send_modal(ReportModal(p["targetId"], them.get("displayName", "người này") if them else "người này"))
            
        elif kind == "unmatch_ask":
            view = discord.ui.View()
            view.add_item(discord.ui.Button(custom_id=ID.noop(), label="Thôi", style=discord.ButtonStyle.secondary))
            view.add_item(discord.ui.Button(custom_id=ID.unmatch_do(p["matchId"]), label="Hủy match", style=discord.ButtonStyle.danger))
            await i.response.send_message(embed=notice(color=COLOR["crimson"], title="Hủy match?", body="Phòng chat sẽ bị khoá và hai bạn không thấy lại nhau nữa.", footer="Không thể hoàn tác."), view=view, ephemeral=True)

        elif kind == "noop":
            await i.response.edit_message(embed=notice(color=COLOR["slate"], title="Đã hủy"), view=None)

    async def on_modal(self, i: discord.Interaction, p: dict, guild_id: str):
        kind = p["kind"]
        
        if kind == "profile_modal":
            # Logic gọi handle_basics hoặc handle_prompts ở đây
            pass
            
        elif kind == "superlike_note":
            note = i.data["components"][0]["components"][0]["value"]
            if i.message:
                await i.response.defer()
                await self.apply_superlike(i, guild_id, p["targetId"], note)
            else:
                await i.response.defer(ephemeral=True)
                res = await send_superlike(guild_id, i.user.id, p["targetId"], note)
                embed = notice(color=COLOR["violet"], title="Hết Super Like" if res["kind"] == "no_balance" else "Bạn đã Super Like người này rồi" if res["kind"] == "already_sent" else f"{GLYPH['superLike']} Đã gửi Super Like")
                await i.followup.send(embed=embed)

    # ─────────────────────────────────────────────────────────────────────────
    # CÁC HÀM XỬ LÝ LÕI
    # ─────────────────────────────────────────────────────────────────────────
    
    async def build_swipe_view(self, i: discord.Interaction, guild_id: str) -> dict:
        me = await get_profile(guild_id, i.user.id)
        if not me: return {"embeds": [notice(color=COLOR["rose"], title="Bạn chưa có hồ sơ")]}
        
        missing = missing_fields(me)
        if missing:
            view = discord.ui.View().add_item(discord.ui.Button(custom_id=ID.profile_setup(), label="Hoàn tất hồ sơ", style=discord.ButtonStyle.success))
            return {"embed": notice(color=COLOR["slate"], title="Hoàn tất hồ sơ trước đã", body="\n".join([f"• {m}" for m in missing])), "view": view}

        await touch_activity(guild_id, i.user.id)
        # Các logic lướt sẽ gọi tới `dating_discovery`
        # ...
        return {"embed": notice(color=COLOR["slate"], title="Hết hồ sơ rồi")}

    async def swipe_button(self, i: discord.Interaction, guild_id: str, action: str, target_id: str):
        if action == "super":
            supers = await get_superlikes(guild_id, i.user.id)
            if supers <= 0:
                await i.response.send_message(embed=notice(color=COLOR["violet"], title="Hết Super Like", body="Hỏi mod xem server có phát không."), ephemeral=True)
                return
            if await has_superliked(guild_id, i.user.id, target_id):
                await i.response.send_message(embed=notice(color=COLOR["violet"], title="Bạn đã Super Like người này rồi"), ephemeral=True)
                return
            
            them = await get_profile(guild_id, target_id)
            await i.response.send_modal(SuperLikeNoteModal(target_id, them.get("displayName", "họ") if them else "họ"))
            return

        await i.response.defer()
        await self.apply_swipe(i, guild_id, target_id, "LIKE" if action == "like" else "PASS")

    async def apply_swipe(self, i: discord.Interaction, guild_id: str, target_id: str, action: str):
        res = await record_swipe(guild_id, i.user.id, target_id, action)
        if res["kind"] == "matched":
            await announce_match(self.bot, res["matchId"])
            await i.followup.send(embed=notice(color=COLOR["gold"], title=f"{GLYPH['sparkle']} Match!", body="Bot đã nhắn tin riêng cho cả hai."), ephemeral=True)
        
        next_view = await self.build_swipe_view(i, guild_id)
        await i.edit_original_response(**next_view)

    async def match_button(self, i: discord.Interaction, p: dict):
        if p["kind"] == "match_decline":
            await decline_match(p["matchId"], i.user.id)
            await i.response.edit_message(embed=notice(color=COLOR["slate"], title="Đã bỏ qua", footer="Người kia không được báo là bạn từ chối."), view=None)
            return

        await i.response.defer()
        res = await mark_ready(self.bot, p["matchId"], i.user.id)
        # Setup Card tương ứng res["kind"]
        await i.edit_original_response(embed=notice(color=COLOR["gold"], title="Đã ghi nhận"), view=None)

async def setup(bot):
    await bot.add_cog(DatingRouter(bot))
