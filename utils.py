import os
import json
import firebase_admin
from firebase_admin import credentials, db
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_DB_URL = "https://ai-postmakerbot-default-rtdb.asia-southeast1.firebasedatabase.app"
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")

# تهيئة Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })

def get_user_data(user_id: int):
    ref = db.reference(f"/users/{user_id}")
    data = ref.get()
    if data is None:
        return {"count": 0}
    return data

def save_user_data(user_id: int, data: dict):
    ref = db.reference(f"/users/{user_id}")
    ref.set(data)

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    data = get_user_data(user_id)
    return data.get("count", 0) < limit

def increment_user_count(user_id: int):
    data = get_user_data(user_id)
    data["count"] = data.get("count", 0) + 1
    save_user_data(user_id, data)

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception:
        return False

def require_subscription(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            subscribed = await is_user_subscribed(user_id, context)
        except Exception:
            await update.message.reply_text("⚠️ حدث خطأ أثناء التحقق من الاشتراك.")
            return

        if not subscribed:
            await update.message.reply_text(
                f"❌ يجب عليك الاشتراك أولاً في القناة للاستفادة من خدمات البوت:\n\nhttps://t.me/{REQUIRED_CHANNEL.replace('@', '')}"
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

# دالة جديدة: الحصول على عدد الطلبات المستخدمة
def get_user_count(user_id: int) -> int:
    data = get_user_data(user_id)
    return data.get("count", 0)
