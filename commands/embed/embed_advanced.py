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
            description=f"**yiyi** không tìm thấy embed tên `{name}` để xuất mã.",
            color=0xf8bbd0
        )
        return await interaction.followup.send(embed=embed_err)

    try:
        # [IT PRO] Nén JSON thành chuỗi Base64 siêu ngắn
        json_bytes = json.dumps(data).encode('utf-8')
        compressed = zlib.compress(json_bytes)
        export_code = base64.urlsafe_b64encode(compressed).decode('utf-8')
        
        # CHỈ THAY ĐỔI: Chuyển từ Embed sang Content thuần túy
        response_text = (
            f"tạo mã thành công, có thể sao chép mã bên dưới để sử dụng\n"
            f"lưu ý: **không được** chỉnh sửa đoạn mã này, nếu không mã sẽ không hợp lệ.\n\n"
            f"**{export_code}**\n\n"
            f"```\n{export_code}\n```"
        )
        
        await interaction.followup.send(content=response_text)
        
    except Exception as e:
        await interaction.followup.send(f"có lỗi xảy ra khi xuất mã: {e}")


@app_commands.command(name="import", description="nhập đoạn mã export để tạo embed mới")
async def import_cmd(interaction: discord.Interaction, name: str, code: str):
    await interaction.response.defer(ephemeral=False)
    
    if await load_embed(interaction.guild.id, name):
        embed_err = discord.Embed(
            title=f"{Emojis.MATTRANG} tên embed đã tồn tại",
            description=f"tên `{name}` đã được sử dụng, cậu hãy chọn tên khác nhé.",
            color=0xf8bbd0
        )
        return await interaction.followup.send(embed=embed_err)

    try:
        # Giải nén mã Code ngược lại thành JSON
        decoded = base64.urlsafe_b64decode(code.strip().encode('utf-8'))
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
        return await interaction.followup.send(f"{Emojis.HOICHAM} tên `{name}` đã tồn tại, cậu hãy chọn tên khác nhé")

    # Dùng Regex móc bóc tách ID kênh và ID tin nhắn từ URL
    match = re.search(r'channels/\d+/(\d+)/(\d+)', link)
    if not match:
        return await interaction.followup.send(f"{Emojis.HOICHAM} link tin nhắn không hợp lệ.")
        
    channel_id, msg_id = int(match.group(1)), int(match.group(2))
    
    try:
        channel = interaction.client.get_channel(channel_id) or await interaction.client.fetch_channel(channel_id)
        msg = await channel.fetch_message(msg_id)
        
        if not msg.embeds:
            return await interaction.followup.send(f"{Emojis.HOICHAM} tin nhắn này không có embed nào cả.")
            
        # [CORE] Ép kiểu từ Discord Embed sang Dictionary của PeiD
        raw_dict = msg.embeds[0].to_dict()
        
        # Dọn dẹp rác hệ thống của Discord
        clean_data = {
            "title": raw_dict.get("title"),
            "description": raw_dict.get("description"),
            "color": raw_dict.get("color", 0xf8bbd0),
            "image": raw_dict.get("image", {}).get("url"),
            "thumbnail": raw_dict.get("thumbnail", {}).get("url"),
            "author": {"name": raw_dict.get("author", {}).get("name"), "icon_url": raw_dict.get("author", {}).get("icon_url")},
            "footer": {"text": raw_dict.get("footer", {}).get("text"), "icon_url": raw_dict.get("footer", {}).get("icon_url")}
        }
        
        clean_data = {k: v for k, v in clean_data.items() if v}
        
        await save_embed(interaction.guild.id, name, clean_data)
        
        embed_success = discord.Embed(
            title=f"{Emojis.YIYITIM} clone thành công!",
            description=f"đã chép embed thành công với tên `{name}`. cậu hãy dùng `/p embed edit` để chỉnh sửa nhé",
            color=0xf8bbd0
        )
        await interaction.followup.send(embed=embed_success)
        
    except Exception as e:
        print(f"[clone error] {e}")
        await interaction.followup.send(f"{Emojis.HOICHAM} có lỗi xảy ra: **yiyi** không thể đọc được tin nhắn này.")

# =============================
# INJECTION
# =============================
async def setup(bot: commands.Bot):
    p_cmd = bot.tree.get_command("p")
    if p_cmd and isinstance(p_cmd, app_commands.Group):
        embed_group = next((cmd for cmd in p_cmd.commands if cmd.name == "embed" and isinstance(cmd, app_commands.Group)), None)
                
        if embed_group:
            # Gỡ bỏ lệnh cũ để tránh trùng lặp khi reload
            for cmd_name in ["export", "import", "clone"]:
                existing = next((c for c in embed_group.commands if c.name == cmd_name), None)
                if existing: embed_group.remove_command(cmd_name)

            embed_group.add_command(export_cmd)
            embed_group.add_command(import_cmd)
            embed_group.add_command(clone_cmd)
            print("[load] success: commands.embed.embed_advanced (text mode)", flush=True)


