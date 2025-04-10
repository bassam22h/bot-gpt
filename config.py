import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

# تعديل الكود ليتجنب الخطأ إذا كانت القيمة فارغة
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_IDS = [int(x) for x in admin_ids_str.split(",") if x.strip().isdigit()]
else:
    ADMIN_IDS = []
