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
# AUTOCOMPLETE HELPER
# =============================
async def embed_name_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild: return []
    names = await get_all_embed_names(guild.id)
    return [app_commands.Choice(name=name, value=name) for name in names if current.lower() in name.lower()][:25]

# =============================
# ADVANCED COMMANDS
# =============================

@app_commands.command(name="export", description="xuất embed thành đoạn mã code để chia sẻ")
@app_commands.autocomplete(name=embed_name_autocomplete)
async def export_cmd(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=False)
    
    data = await load_embed(interaction.guild.id, name)
    if not data:
        embed_err = discord.Embed(
            title=f"{Emojis.HOICHAM} không tìm thấy embed",
            description=f"**yiyi** không tìm thấy embed `{name}` để xuất mã.",
            color=0xf8bbd0
        )
        return await interaction.followup.send(embed=embed_err)

    try:
        # [IT PRO] Nén JSON thành chuỗi Base64 siêu ngắn (chuẩn công nghiệp)
        json_bytes = json.dumps(data).encode('utf-8')
        compressed = zlib.compress(json_bytes)
        export_code = base64.urlsafe_b64encode(compressed).decode('utf-8')
        
        embed = discord.Embed(
            title=f"{Emojis.MATTRANG} mã export của `{name}`",
            description=f"cậu có thể gửi đoạn mã này cho người khác dùng lệnh `/p embed import` để sao chép.\n\n```yaml\n{export_code}\n```",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"có lỗi xảy ra khi xuất mã: {e}")


@app_commands.command(name="import", description="nhập đoạn mã export để tạo embed mới")
async def import_cmd(interaction: discord.Interaction, name: str, code: str):
    await interaction.response.defer(ephemeral=False)
    
    if await load_embed(interaction.guild.id, name):
        embed_err = discord.Embed(
            title=f"{Emojis.MATTRANG} tên embed đã tồn tại",
            description=f"tên `{name}` đã được sử dụng, xin hãy chọn tên khác nhé.",
            color=0xf8bbd0
        )
        return await interaction.followup.send(embed=embed_err)

    try:
        # Giải nén mã Code ngược lại thành JSON
        decoded = base64.urlsafe_b64decode(code.encode('utf-8'))
        decompressed = zlib.decompress(decoded).decode('utf-8')
        data = json.loads(decompressed)
        
        # Lưu vào nhà kho
        await save_embed(interaction.guild.id, name, data)
        
        embed = discord.Embed(
            title=f"{Emojis.YIYITIM} import thành công!",
            description=f"đã sao chép thành công. cậu dùng `/p embed edit name:{name}` để xem lại nhé.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed)
    except Exception:
        embed_fail = discord.Embed(
            title=f"{Emojis.HOICHAM} mã import không hợp lệ",
            description="đoạn mã này đã bị hỏng hoặc không đúng định dạng của **yiyi**.",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_fail)


@app_commands.command(name="clone", description="copy embed từ một tin nhắn discord bất kỳ")
@app_commands.describe(link="dán link tin nhắn chứa embed vào đây", name="tên embed muốn lưu")
async def clone_cmd(interaction: discord.Interaction, name: str, link: str):
    await interaction.response.defer(ephemeral=False)
    
    if await load_embed(interaction.guild.id, name):
        return await interaction.followup.send(f"{Emojis.HOICHAM} tên `{name}` đã tồn tại rồi.")

    # Dùng Regex móc bóc tách ID kênh và ID tin nhắn từ URL
    match = re.search(r'channels/\d+/(\d+)/(\d+)', link)
    if not match:
        return await interaction.followup.send(f"{Emojis.HOICHAM} link tin nhắn không hợp lệ.")
        
    channel_id, msg_id = int(match.group(1)), int(match.group(2))
    
    try:
        channel = interaction.client.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không tìm thấy kênh này. (có thể yiyi chưa được vào kênh đó)")
            
        msg = await channel.fetch_message(msg_id)
        if not msg.embeds:
            return await interaction.followup.send(f"{Emojis.HOICHAM} tin nhắn này không có embed nào cả.")
            
        # [CORE] Ép kiểu từ Discord Embed sang Dictionary của PeiD
        raw_dict = msg.embeds[0].to_dict()
        
        # Dọn dẹp rác hệ thống của Discord (giữ lại các trường hiển thị)
        clean_data = {
            "title": raw_dict.get("title"),
            "description": raw_dict.get("description"),
            "color": raw_dict.get("color", 0xf8bbd0),
            "image": raw_dict.get("image", {}).get("url"),
            "thumbnail": raw_dict.get("thumbnail", {}).get("url"),
            "author": {"name": raw_dict.get("author", {}).get("name"), "icon_url": raw_dict.get("author", {}).get("icon_url")},
            "footer": {"text": raw_dict.get("footer", {}).get("text"), "icon_url": raw_dict.get("footer", {}).get("icon_url")}
        }
        
        # Cắt bỏ các key rỗng để chuẩn hóa form
        clean_data = {k: v for k, v in clean_data.items() if v}
        
        await save_embed(interaction.guild.id, name, clean_data)
        
        embed_success = discord.Embed(
            title=f"{Emojis.YIYITIM} clone thành công!",
            description=f"đã chép embed thành công với tên `{name}`. dùng `/p embed edit` để tinh chỉnh nhé!",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_success)
        
    except discord.NotFound:
        await interaction.followup.send(f"{Emojis.HOICHAM} không tìm thấy tin nhắn (có thể đã bị xóa).")
    except discord.Forbidden:
        await interaction.followup.send(f"{Emojis.HOICHAM} **yiyi** không có quyền đọc lịch sử tin nhắn kênh đó.")
    except Exception as e:
        print(f"[clone error] {e}")
        await interaction.followup.send(f"có lỗi xảy ra: không thể clone lúc này.")

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        # Tìm group "embed" bên trong group "p"
        embed_group = None
        for cmd in p_cmd.commands:
            if cmd.name == "embed" and isinstance(cmd, app_commands.Group):
                embed_group = cmd
                break
                
        if embed_group:
            # Gắn 3 lệnh mới vào hệ thống /p embed ...
            embed_group.add_command(export_cmd)
            embed_group.add_command(import_cmd)
            embed_group.add_command(clone_cmd)
            print("[load] success: commands.embed.embed_advanced (export/import/clone)", flush=True)
        else:
            print("[error] không tìm thấy lệnh /p embed để tiêm mã nâng cao.", flush=True)


