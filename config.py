import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # مثلاً: "@mychannel"
CHANNEL_LINK = os.getenv("CHANNEL_LINK")          # مثلاً: "https://t.me/mychannel"

# يدعم أكثر من مشرف: يجب إدخال المعرفات مفصولة بفواصل في متغير ADMIN_IDS على Render
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
