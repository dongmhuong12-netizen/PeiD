@app_commands.command(name="delete", description="Delete embed")
async def delete(self, interaction: discord.Interaction, name: str):

    from core.embed_ui import ACTIVE_EMBED_VIEWS

    delete_embed(name)

    # 🔥 Xoá toàn bộ UI
    if name in ACTIVE_EMBED_VIEWS:
        for view in ACTIVE_EMBED_VIEWS[name]:
            try:
                if view.message:
                    await view.message.delete()
            except:
                pass
            view.stop()

        ACTIVE_EMBED_VIEWS[name] = []

    await interaction.response.send_message(
        f"🗑 Embed `{name}` UI deleted everywhere."
    )
