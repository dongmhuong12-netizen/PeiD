import discord
from core.dating_storage import get_guild_config
from core.dating_permissions import is_dev_user

async def check_gate(interaction: discord.Interaction) -> dict:
    """
    Cổng kiểm tra an ninh trước MỌI hành động hẹn hò.
    Đảm bảo Server đã cấu hình Bot và User có Role xác minh độ tuổi.
    """
    if not interaction.guild_id:
        return {"ok": False, "reason": "Chỉ dùng được tính năng này trong server."}

    cfg = await get_guild_config(interaction.guild_id)
    
    if not cfg or not cfg.get("enabled"):
        return {
            "ok": False,
            "reason": "Bot chưa được bật ở server này. Nhờ chủ server chạy `/cupid setup`."
        }
        
    verified_role_id = cfg.get("verifiedRoleId")
    if not verified_role_id:
        return {
            "ok": False, 
            "reason": "Server chưa cấu hình xong. Nhờ admin chạy lại lệnh setup."
        }

    # Dev toàn cục lách mọi luật lệ an ninh Role
    if is_dev_user(interaction.user.id):
        return {"ok": True, "guildId": str(interaction.guild_id), "cfg": cfg}

    # Kiểm tra quyền Member
    if isinstance(interaction.user, discord.Member):
        # Lấy danh sách ID của các role mà user đang sở hữu
        role_ids = [str(r.id) for r in interaction.user.roles]
        
        if str(verified_role_id) in role_ids:
            return {"ok": True, "guildId": str(interaction.guild_id), "cfg": cfg}

    # Nếu không có role -> Đuổi thẳng cổ
    return {
        "ok": False,
        "reason": f"Bạn cần role <@&{verified_role_id}> để dùng bot.\nLiên hệ mod của server để được cấp."
    }
