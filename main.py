import os
from core.bot import create_bot

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ TOKEN not found.")

bot = create_bot()

if __name__ == "__main__":
    bot.run(TOKEN)
