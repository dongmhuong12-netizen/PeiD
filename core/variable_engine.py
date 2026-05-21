import discord
from typing import Union
import time
import re
# [CẤY MỚI] Import kho chứa emoji để chuẩn bị trích xuất thực thể đồ họa
from utils.emojis import Emojis

def build_variables(
    guild: discord.Guild,
    member: Union[discord.Member, discord.User, None] = None
) -> dict:
    """
    Xây dựng từ điển biến số. 
    Tối ưu hóa tuyệt đối để không làm treo Bot ở server 100k+.
    """
    variables = {}

    # =========================
    # MEMBER VARIABLES (Nhẹ)
    # =========================
    if member:
        # [TỐI ƯU] Dùng getattr để kháng lỗi Crash nếu thực thể trả về là User thay vì Member
        joined_at = getattr(member, "joined_at", None)
        created_at = getattr(member, "created_at", None)
        
        joined_str = joined_at.strftime("%d/%m/%Y") if joined_at else "Chưa rõ"
        created_str = created_at.strftime("%d/%m/%Y") if created_at else "Chưa rõ"

        roles = getattr(member, "roles", [])
        top_role = getattr(member, "top_role", None)

        variables.update({
            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_display}": member.display_name,
            "{user_tag}": str(member),
            "{user_id}": str(member.id),
            "{user_avatar}": member.display_avatar.url if getattr(member, "display_avatar", None) else "",
            "{user_bot}": "Có" if member.bot else "Không",
            "{user_created}": created_str,
            "{user_joined}": joined_str,
            "{user_role_count}": str(len(roles) - 1) if roles else "0",
            "{user_top_role}": top_role.mention if top_role else "Không có",
        })

    # =========================
    # SERVER VARIABLES (Atomic Data)
    # =========================
    # [TỐI ƯU] Bọc Guild Check để an toàn tuyệt đối khi tương tác qua DM / Webhook mồ côi
    if guild:
        # [VÁ LỖI] Luôn dùng Owner ID để tạo mention, tránh trả về "Không rõ" ở server lớn
        server_owner_mention = guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"

        variables.update({
            "{server}": guild.name,
            "{server_name}": guild.name,
            "{server_id}": str(guild.id),
            "{server_owner}": server_owner_mention,
            "{server_owner_id}": str(guild.owner_id),
            "{server_created}": guild.created_at.strftime("%d/%m/%Y") if guild.created_at else "Chưa rõ",
            "{server_icon}": guild.icon.url if guild.icon else "",
            "{member_count}": str(guild.member_count or 0),
            "{boost_count}": str(guild.premium_subscription_count or 0),
            "{boost_level}": str(guild.premium_tier),
            "{role_count}": str(len(guild.roles)),
            "{channel_count}": str(len(guild.channels)),
            "{emoji_count}": str(len(guild.emojis)),
        })

        # =========================
        # HEAVY CALCULATIONS (Cơ chế bảo vệ CPU)
        # =========================
        # [TỐI ƯU] Chỉ đếm nếu server thực sự nhỏ và đã nạp đủ cache
        if guild.member_count and guild.member_count < 5000:
            members = guild.members
            if len(members) >= guild.member_count * 0.9: 
                bot_count = sum(1 for m in members if m.bot)
                variables.update({
                    "{bot_count}": str(bot_count),
                    "{human_count}": str(len(members) - bot_count),
                    "{online_count}": str(sum(1 for m in members if m.status != discord.Status.offline)),
                })
            else:
                variables.update({"{bot_count}": "...", "{human_count}": "...", "{online_count}": "..."})
        else:
            # Với server > 5k, dùng số liệu tổng quát để bảo vệ tài nguyên
            variables.update({
                "{bot_count}": "N/A",
                "{human_count}": str(guild.member_count or 0),
                "{online_count}": "N/A",
            })

    # =========================
    # TIME VARIABLES
    # =========================
    now = discord.utils.utcnow()
    unix = str(int(time.time()))

    variables.update({
        "{timestamp}": unix,
        "{unix}": unix,
        "{date}": now.strftime("%d/%m/%Y"),
        "{time}": now.strftime("%H:%M:%S"),
    })

    # =========================================================================
    # [CẤY MỚI] AUTOMATIC EMOJI INJECTION MODULE
    # Tự động quét lớp phản chiếu bóc toàn bộ Emoji từ Class
    # =========================================================================
    try:
        for attr, val in Emojis.__dict__.items():
            if not attr.startswith("__") and isinstance(val, str):
                variables[f"{{{attr.lower()}}}"] = val
                variables[f"{{{attr.upper()}}}"] = val
    except Exception:
        pass

    return variables


def apply_variables(
    data: Union[str, dict, list],
    guild: discord.Guild,
    member: Union[discord.Member, discord.User, None] = None
) -> Union[str, dict, list]:
    """
    Áp dụng biến số vào dữ liệu bằng Regex tối ưu.
    """
    if not data:
        return data

    variables = build_variables(guild, member)
    
    # [PHÒNG THỦ] Tránh compile rỗng nếu variables gặp sự cố
    if not variables:
        return data
        
    # [TỐI ƯU CỰC ĐẠI] Sắp xếp khóa theo độ dài giảm dần (Descending Length Sort)
    # Ngăn chặn lỗi Regex "nuốt" một phần biến (Vd: Nuốt {user} bên trong {user_name})
    sorted_keys = sorted(variables.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in sorted_keys))

    def replace_value(value):
        if isinstance(value, str):
            if "{" not in value:
                return value
            # Thay thế thần tốc bằng Regex
            return pattern.sub(lambda m: variables.get(m.group(0), m.group(0)), value)

        if isinstance(value, dict):
            return {k: replace_value(v) for k, v in value.items()}

        if isinstance(value, list):
            return [replace_value(v) for v in value]

        return value

    return replace_value(data)
