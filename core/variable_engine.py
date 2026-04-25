import discord
from typing import Union
import time
import re

def build_variables(
    guild: discord.Guild,
    member: discord.Member | None = None
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
        joined_at = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Chưa rõ"
        created_at = member.created_at.strftime("%d/%m/%Y") if member.created_at else "Chưa rõ"

        variables.update({
            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_display}": member.display_name,
            "{user_tag}": str(member),
            "{user_id}": str(member.id),
            "{user_avatar}": member.display_avatar.url,
            "{user_bot}": "Có" if member.bot else "Không",
            "{user_created}": created_at,
            "{user_joined}": joined_at,
            "{user_role_count}": str(len(member.roles) - 1),
            "{user_top_role}": member.top_role.mention if member.top_role else "Không có",
        })

    # =========================
    # SERVER VARIABLES (Atomic Data)
    # =========================
    # Dùng các thuộc tính có sẵn của discord.py để tránh duyệt list
    variables.update({
        "{server}": guild.name,
        "{server_name}": guild.name,
        "{server_id}": str(guild.id),
        "{server_owner}": guild.owner.mention if guild.owner else "Không rõ",
        "{server_owner_id}": str(guild.owner_id),
        "{server_created}": guild.created_at.strftime("%d/%m/%Y"),
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
    # Chỉ tính toán online/bot count nếu server dưới 10k người hoặc cache đã sẵn sàng
    if guild.member_count and guild.member_count < 10000:
        members = guild.members
        if len(members) >= guild.member_count * 0.8: # Cache phải đủ 80% mới đếm
            bot_count = sum(1 for m in members if m.bot)
            variables.update({
                "{bot_count}": str(bot_count),
                "{human_count}": str(len(members) - bot_count),
                "{online_count}": str(sum(1 for m in members if m.status != discord.Status.offline)),
            })
        else:
            variables.update({"{bot_count}": "Đang nạp...", "{human_count}": "Đang nạp...", "{online_count}": "Đang nạp..."})
    else:
        # Với server cực lớn, dùng số liệu tổng quát để tránh treo Bot
        variables.update({
            "{bot_count}": "N/A (Server lớn)",
            "{human_count}": str(guild.member_count or 0),
            "{online_count}": "N/A (Server lớn)",
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

    return variables


def apply_variables(
    data: Union[str, dict, list],
    guild: discord.Guild,
    member: discord.Member | None = None
) -> Union[str, dict, list]:
    """
    Áp dụng biến số vào dữ liệu bằng Regex tối ưu.
    """
    if data is None:
        return data

    # Chỉ build variables 1 lần duy nhất cho mỗi đợt apply
    variables = build_variables(guild, member)
    
    # Tạo Pattern Regex an toàn (re.escape cực kỳ quan trọng)
    pattern = re.compile("|".join(re.escape(k) for k in variables.keys()))

    def replace_value(value):
        if isinstance(value, str):
            # Check nhanh để bỏ qua chuỗi không chứa biến
            if "{" not in value:
                return value
            # Thay thế thần tốc bằng Regex
            return pattern.sub(lambda m: variables[m.group(0)], value)

        if isinstance(value, dict):
            # Dùng dict comprehension cho tốc độ Atomic
            return {k: replace_value(v) for k, v in value.items()}

        if isinstance(value, list):
            return [replace_value(v) for v in value]

        return value

    return replace_value(data)
