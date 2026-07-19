import logging
import time
from urllib.parse import urlparse, parse_qs
import discord
from core.dating_storage import profiles_col

log = logging.getLogger("dating.photo")

MAX_BYTES = 8 * 1024 * 1024  # 8MB
ALLOWED = ["image/png", "image/jpeg", "image/webp"]

# Chỉ chấp nhận ảnh tải thẳng lên Discord, chống user chèn link ngoài ăn cắp IP
CDN_HOSTS = ["cdn.discordapp.com", "media.discordapp.net"]

def validate_photo(attachment: discord.Attachment) -> dict:
    """Kiểm tra tính hợp lệ của ảnh được gửi lên"""
    try:
        host = urlparse(attachment.url).hostname.lower()
    except Exception:
        host = None

    if not host or host not in CDN_HOSTS:
        return {"ok": False, "error": "Ảnh phải được tải trực tiếp lên Discord."}
    
    # MIME type được Discord tự nhận diện, cực kỳ an toàn
    content_type = attachment.content_type.split(";")[0].strip() if attachment.content_type else ""
    if content_type not in ALLOWED:
        return {"ok": False, "error": "Chỉ nhận ảnh PNG, JPG hoặc WEBP."}
    
    if attachment.size > MAX_BYTES:
        return {"ok": False, "error": "Ảnh quá lớn (tối đa 8MB)."}
    
    if not attachment.width or not attachment.height:
        return {"ok": False, "error": "File này không phải ảnh hợp lệ."}
    
    if attachment.width < 200 or attachment.height < 200:
        return {"ok": False, "error": "Ảnh quá nhỏ (tối thiểu 200x200)."}
    
    return {"ok": True, "url": attachment.url}

def is_stale(url: str) -> bool:
    """Kiểm tra xem link Discord CDN đã hết hạn (hoặc sắp hết hạn trong 1h tới) chưa"""
    try:
        query = urlparse(url).query
        params = parse_qs(query)
        if 'ex' in params:
            # Discord lưu thời gian hết hạn dưới dạng mã Hex ở tham số 'ex'
            expires_at = int(params['ex'][0], 16)
            # Refresh nếu thời gian sống còn dưới 1 tiếng (3600 giây)
            return time.time() > (expires_at - 3600)
    except Exception:
        pass
    return False

async def refresh_photos(client: discord.Client, profiles: list) -> dict:
    """Xin lại lô link ảnh mới từ Discord API và lưu thẳng vào MongoDB"""
    out = {}
    stale_profiles = [p for p in profiles if p.get("photoUrl") and is_stale(p["photoUrl"])]
    
    if not stale_profiles:
        return out

    try:
        # Endpoint của Discord nhận tối đa 50 link mỗi lần
        for i in range(0, len(stale_profiles), 50):
            batch = stale_profiles[i:i+50]
            urls = [p["photoUrl"] for p in batch]
            
            # Chọc thẳng vào REST API của Discord để xin link mới
            route = discord.http.Route('POST', '/attachments/refresh-urls')
            res = await client.http.request(route, json={"attachment_urls": urls})
            
            if "refreshed_urls" in res:
                by_original = {item["original"]: item["refreshed"] for item in res["refreshed_urls"]}
                
                for p in batch:
                    fresh_url = by_original.get(p["photoUrl"])
                    if not fresh_url or fresh_url == p["photoUrl"]:
                        continue
                    
                    out[p["_id"]] = fresh_url
                    
                    # Update ngược dòng link mới tinh vào DB
                    await profiles_col.update_one(
                        {"_id": p["_id"]},
                        {"$set": {"photoUrl": fresh_url}}
                    )
    except Exception as e:
        # Nếu Discord chập cheng, bỏ qua lỗi để bot vẫn chạy tiếp được
        log.warning(f"Làm mới URL ảnh thất bại: {e}")
        
    return out

async def with_fresh_photo(client: discord.Client, profile: dict) -> dict:
    """Bọc mồi làm mới ảnh trước khi render Card"""
    if not profile.get("photoUrl") or not is_stale(profile["photoUrl"]):
        return profile
    
    fresh_map = await refresh_photos(client, [profile])
    fresh_url = fresh_map.get(profile.get("_id"))
    
    if fresh_url:
        profile["photoUrl"] = fresh_url
        
    return profile
