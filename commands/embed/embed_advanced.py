import discord
from discord import app_commands
from discord.ext import commands
import json
import base64
import zlib
import re

from core.embed_storage import load_embed, save_embed, get_all_embed_names
from utils.emojis import Emojis

# =============================
# AUTOCOMPLETE HELPER (GIỮ NGUYÊN)
# =============================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    try:
        names = await get_all_embed_names(guild.id)
        return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]
    except: return []

# =============================
# ADVANCED COMMANDS (MAX DEF/ATK)
# =============================

@app_commands.command(name="export", description="xuất embed thành đoạn mã code để chia sẻ")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def export_cmd(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=False)
    
    data = await load_embed(interaction.guild.id, name)
    if not data:
        return await interaction.followup.send(content=f"{Emojis.HOICHAM} **yiyi** không tìm thấy embed tên `{name}` để xuất mã.")

    try:
        # [IT PRO] Nén JSON thành chuỗi Base64 siêu ngắn
        json_bytes = json.dumps(data).encode('utf-8')
        compressed = zlib.compress(json_bytes)
        export_code = base64.urlsafe_b64encode(compressed).decode('utf-8')
        
        response_text = (
            f"{Emojis.MATTRANG} tạo mã thành công, có thể sao chép mã bên dưới để sử dụng\n"
            f"lưu ý: **không được** chỉnh sửa đoạn mã này để tránh lỗi hệ thống.\n\n"
            f"```\n{export_code}\n
```"
        )
        await interaction.followup.send(content=response_text)
    except Exception as e:
        await interaction.followup.send(content=f"có lỗi khi nén mã: {e}")


@app_commands.command(name="import", description="nhập đoạn mã export để tạo embed mới")
async def import_cmd(interaction: discord.Interaction, name: str, code: str):
    await interaction.response.defer(ephemeral=False)
    
    if await load_embed(interaction.guild.id, name):
        return await interaction.followup.send(content=f"{Emojis.HOICHAM} tên `{name}` đã tồn tại, cậu hãy chọn tên khác nhé.")

    try:
        # Giải nén mã Code ngược lại thành JSON
        decoded = base64.urlsafe_b64decode(code.strip().encode('utf-8'))
        decompressed = zlib.decompress(decoded).decode('utf-8')
        data = json.loads(decompressed)
        
        await save_embed(interaction.guild.id, name, data)
        await interaction.followup.send(content=f"{Emojis.YIYITIM} import thành công! cậu dùng `/p embed edit name:{name}` để xem lại nhé.")
    except Exception:
        await interaction.followup.send(content=f"{Emojis.HOICHAM} mã import không hợp lệ hoặc đã bị hỏng.")


@app_commands.command(name="clone", description="copy embed từ một tin nhắn discord bất kỳ")
@app_commands.describe(link="dán link tin nhắn hoặc định dạng channel_id-message_id", name="tên embed muốn lưu")
async def clone_cmd(interaction: discord.Interaction, name: str, link: str):
    await interaction.response.defer(ephemeral=False)
    
    # 1. DEFENSE: Chặn trùng tên
    if await load_embed(interaction.guild.id, name):
        return await interaction.followup.send(content=f"{Emojis.HOICHAM} tên `{name}` đã tồn tại rồi cậu.")

    # 2. ATTACK: Regex vạn năng (Xử lý mọi loại Link: Server, DM, Canary, PTB và cả ID rời)
    # Pattern 1: Link chuẩn Discord (Chấp nhận cả @me cho DM)
    link_match = re.search(r'channels/(\d+|@me)/(\d+)/(\d+)', link)
    # Pattern 2: Định dạng ID rời (channel_id-message_id)
    id_match = re.search(r'(\d+)[\-/](\d+)', link)

    if link_match:
        c_id, m_id = int(link_match.group(2)), int(link_match.group(3))
    elif id_match:
        c_id, m_id = int(id_match.group(1)), int(id_match.group(2))
    else:
        return await interaction.followup.send(content=f"{Emojis.HOICHAM} link hoặc ID tin nhắn không hợp lệ rồi cậu ơi.")
    
    try:
        # 3. Mạch fetch tin nhắn xuyên thấu
        channel = interaction.client.get_channel(c_id) or await interaction.client.fetch_channel(c_id)
        msg = await channel.fetch_message(m_id)
        
        if not msg.embeds:
            return await interaction.followup.send(content=f"{Emojis.HOICHAM} tin nhắn này làm gì có embed nào đâu nè?")
            
        # 4. DEEP CLONE: Bóc tách toàn bộ linh kiện (bao gồm cả Fields)
        raw = msg.embeds[0].to_dict()
        
        # Lọc sạch rác hệ thống, giữ lại hồn cốt Embed
        clean_data = {
            "title": raw.get("title"),
            "description": raw.get("description"),
            "color": raw.get("color"),
            "image": raw.get("image", {}).get("url"),
            "thumbnail": raw.get("thumbnail", {}).get("url"),
            "author": {
                "name": raw.get("author", {}).get("name"), 
                "icon_url": raw.get("author", {}).get("icon_url")
            } if raw.get("author") else None,
            "footer": {
                "text": raw.get("footer", {}).get("text"), 
                "icon_url": raw.get("footer", {}).get("icon_url")
            } if raw.get("footer") else None,
            "fields": [
                {"name": f.get("name"), "value": f.get("value"), "inline": f.get("inline", False)} 
                for f in raw.get("fields", [])
            ]
        }
        
        # Loại bỏ các key rỗng để tối ưu dung lượng DB
        clean_data = {k: v for k, v in clean_data.items() if v is not None}
        if "author" in clean_data: clean_data["author"] = {k: v for k, v in clean_data["author"].items() if v}
        if "footer" in clean_data: clean_data["footer"] = {k: v for k, v in clean_data["footer"].items() if v}
        
        # 5. Lưu kho
        await save_embed(interaction.guild.id, name, clean_data)
        
        await interaction.followup.send(content=f"{Emojis.YIYITIM} clone thành công embed `{name}`! giờ cậu có thể dùng `/p embed edit` để "tút" lại theo ý muốn nhé.")
        
    except discord.Forbidden:
        await interaction.followup.send(content=f"{Emojis.HOICHAM} **yiyi** không có quyền xem tin nhắn ở kênh đó, cậu check lại nhé.")
    except Exception as e:
        print(f"[clone error] {e}")
        await interaction.followup.send(content=f"{Emojis.HOICHAM} **yiyi** không đọc được tin nhắn này. (Lỗi: `{type(e).__name__}`)")

# =============================
# INJECTION (BẢO TOÀN LOGIC CŨ)
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
                
        if embed_group:
            for cmd_name in ["export", "import", "clone"]:
                existing = next((c for c in embed_group.commands if c.name == cmd_name), None)
                if existing: embed_group.remove_command(cmd_name)

            embed_group.add_command(export_cmd)
            embed_group.add_command(import_cmd)
            embed_group.add_command(clone_cmd)
            print("[load] success: commands.embed.embed_advanced (Full DEF/ATK Build)", flush=True)
