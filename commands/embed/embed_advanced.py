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
        
        # FIX: Gom mạch f-string trên các dòng hợp lệ để tránh SyntaxError
        response_text = (
            f"{Emojis.BUOMA} tạo mã thành công, có thể sao chép mã bên dưới để sử dụng\n"
            f"lưu ý: **không được** chỉnh sửa đoạn mã này để tránh lỗi hệ thống.\n\n"
            f"```\n{export_code}\n```"

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
        await interaction.followup.send(content=f"{Emojis.BUOMA} import thành công! cậu dùng `/p embed edit name:{name}` để xem và chỉnh sửa thêm nhé.")
    except Exception:
        await interaction.followup.send(content=f"{Emojis.HOICHAM} mã import không hợp lệ hoặc đã bị hỏng.")


@app_commands.command(name="clone", description="copy hàng loạt embed từ link tin nhắn discord")
@app_commands.describe(
    names="tên các embed muốn lưu, cách nhau bởi dấu phẩy (vd: em1, em2)",
    links="dán các link tin nhắn chứa embed, cách nhau bởi dấu phẩy (vd: link1, link2)"
)
async def clone_cmd(interaction: discord.Interaction, names: str, links: str):
    await interaction.response.defer(ephemeral=False)
    
    # Mạch bẻ chuỗi và dọn sạch khoảng trắng dư thừa
    embed_list = [e.strip() for e in names.split(",") if e.strip()]
    link_list = [l.strip() for l in links.split(",") if l.strip()]

    # [KIỂM DUYỆT ĐỊNH LƯỢNG] Tên và Link bắt buộc phải khớp định lượng 1:1
    if len(embed_list) != len(link_list):
        embed_err = discord.Embed(
            title=f"{Emojis.HOICHAM} lượng dữ liệu không đồng nhất",
            description=f"số lượng tên embed (`{len(embed_list)}`) và số lượng link tin nhắn (`{len(link_list)}`) phải bằng nhau",
            color=0xe6e2dd
        )
        return await interaction.followup.send(embed=embed_err)

    success_clones = []
    failed_clones = []

    # [VÒNG LẶP TRUY QUYÉT HÀNG LOẠT]
    for i in range(len(embed_list)):
        target_name = embed_list[i]
        link_input = link_list[i]

        # 1. DEFENSE: Chặn trùng tên trong hàng chờ sao chép
        if await load_embed(interaction.guild.id, target_name):
            failed_clones.append(f"• `{target_name}` tên embed đã tồn tại.")
            continue

        # 2. ATTACK: Logic bóc tách tọa độ vạn năng từ URL Link
        link_match = re.search(r'channels/(\d+|@me)/(\d+)/(\d+)', link_input)
        if not link_match:
            failed_clones.append(f"• `{target_name}` link tin nhắn không hợp lệ")
            continue

        c_id = int(link_match.group(2))
        m_id = int(link_match.group(3))
        
        try:
            # 3. Mạch fetch tin nhắn xuyên thấu
            channel = interaction.client.get_channel(c_id) or await interaction.client.fetch_channel(c_id)
            msg = await channel.fetch_message(m_id)
            
            if not msg.embeds:
                failed_clones.append(f"• `{target_name}` tin nhắn chưa có embed liên kết")
                continue
                
            # 4. DEEP CLONE: Bóc tách linh kiện (Gìn giữ Logic Industrial)
            raw = msg.embeds[0].to_dict()
            
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
            
            clean_data = {k: v for k, v in clean_data.items() if v is not None}
            if "author" in clean_data: clean_data["author"] = {k: v for k, v in clean_data["author"].items() if v}
            if "footer" in clean_data: clean_data["footer"] = {k: v for k, v in clean_data["footer"].items() if v}
            
            # 5. Lưu kho vĩnh viễn
            await save_embed(interaction.guild.id, target_name, clean_data)
            success_clones.append(f"• `{target_name}` (Kênh: <#{c_id}>)")
            
        except discord.Forbidden:
            failed_clones.append(f"• `{target_name}` **yiyi** không có quyền xem tin nhắn, cậu hãy kiểm tra lại quyền của **yiyi** nhé.")
        except Exception as e:
            print(f"[clone error] {e}")
            failed_clones.append(f"• `{target_name}`: **yiyi** không đọc được tin nhắn này. (Lỗi: `{type(e).__name__}`)")

    # [MẠCH XUẤT BÁO CÁO THỰC TRẠNG]
    embed_report = discord.Embed(
        title=f"{Emojis.BUOMA} báo cáo kết quả sao chép hàng loạt",
        color=0xe6e2dd
    )

    if success_clones:
        embed_report.add_field(
            name="Sao chép thành công:", 
            value="\n".join(success_clones), 
            inline=False
        )
    if failed_clones:
        embed_report.add_field(
            name="Thất bại hoặc bỏ qua:", 
            value="\n".join(failed_clones), 
            inline=False
        )

    embed_report.set_footer(text="yiyi iu cậu • hạ tầng lưu trữ hàng loạt")
    await interaction.followup.send(embed=embed_report)

# =============================
# INJECTION (BẢO TOÀN KIẾN TRÚC)
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
            print("[load] success: commands.embed.embed_advanced (Multi-IT Fixed Edition)", flush=True)
