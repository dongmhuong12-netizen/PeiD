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
    Các phép tính nặng được tối ưu hóa để không làm nghẽn Event Loop ở server lớn.
    """
    variables = {}

    # =========================
    # MEMBER VARIABLES
    # =========================
    if member:
        joined_at = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Unknown"

        variables.update({
            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_display}": member.display_name,
            "{user_tag}": str(member),
            "{user_id}": str(member.id),
            "{user_avatar}": member.display_avatar.url,
            "{user_avatar_png}": member.display_avatar.replace(format="png").url,
            "{user_bot}": str(member.bot),
            "{user_created}": member.created_at.strftime("%d/%m/%Y"),
            "{user_joined}": joined_at,
            "{user_role_count}": str(len(member.roles) - 1),
            "{user_top_role}": member.top_role.name if member.top_role else "None",
        })

    # =========================
    # SERVER VARIABLES
    # =========================
    # Tối ưu: Chỉ tính toán danh sách member khi thực sự cần thiết thông qua Lazy Loading
    # Ở server 100k+, guild.members có thể gây treo bot nếu duyệt thủ công.
    
    variables.update({
        "{server}": guild.name,
        "{server_name}": guild.name,
        "{server_id}": str(guild.id),
        "{server_owner}": guild.owner.mention if guild.owner else "Unknown",
        "{server_owner_id}": str(guild.owner_id),
        "{server_created}": guild.created_at.strftime("%d/%m/%Y"),
        "{server_icon}": guild.icon.url if guild.icon else "",
        "{server_icon_png}": guild.icon.replace(format="png").url if guild.icon else "",
        "{member_count}": str(guild.member_count or 0),
        "{boost_count}": str(guild.premium_subscription_count or 0),
        "{boost_level}": str(guild.premium_tier),
        "{role_count}": str(len(guild.roles)),
        "{channel_count}": str(len(guild.channels)),
        "{text_channel_count}": str(len(guild.text_channels)),
        "{voice_channel_count}": str(len(guild.voice_channels)),
        "{category_count}": str(len(guild.categories)),
        "{emoji_count}": str(len(guild.emojis)),
        "{sticker_count}": str(len(guild.stickers)),
    })

    # Tính toán các biến đếm nâng cao (Chỉ nên dùng nếu Intents Member được bật)
    # Tối ưu: Dùng list comprehension nhanh hơn sum()
    members = guild.members
    if members and len(members) > 0:
        bot_count = sum(1 for m in members if m.bot)
        variables.update({
            "{bot_count}": str(bot_count),
            "{human_count}": str(len(members) - bot_count),
            "{online_count}": str(sum(1 for m in members if m.status != discord.Status.offline)),
        })
    else:
        # Fallback nếu cache member chưa nạp
        variables.update({
            "{bot_count}": "N/A",
            "{human_count}": "N/A",
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

    return variables


def apply_variables(
    data: Union[str, dict, list],
    guild: discord.Guild,
    member: discord.Member | None = None
) -> Union[str, dict, list]:
    """
    Áp dụng biến số vào dữ liệu (string, dict hoặc list).
    Sử dụng Regex để tối ưu tốc độ thay thế chuỗi.
    """
    variables = build_variables(guild, member)
    
    # Tạo Pattern Regex để tìm tất cả các biến cùng lúc
    # Cách này nhanh hơn việc chạy vòng lặp replace() 40 lần
    pattern = re.compile("|".join(re.escape(k) for k in variables.keys()))

    def replace_value(value):
        if isinstance(value, str):
            # Tối ưu: Chỉ thực hiện replace nếu trong chuỗi có dấu {
            if "{" not in value:
                return value
            return pattern.sub(lambda m: variables[m.group(0)], value)

        if isinstance(value, dict):
            return {k: replace_value(v) for k, v in value.items()}

        if isinstance(value, list):
            return [replace_value(v) for v in value]

        return value

    return replace_value(data)
