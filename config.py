import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # مثلاً: "@mychannel"
CHANNEL_LINK = os.getenv("CHANNEL_LINK")          # مثلاً: "https://t.me/mychannel"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
