import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

# دعم عدة معرفات مشرف مفصولة بفواصل
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
