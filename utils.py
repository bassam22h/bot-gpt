import os
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import firebase_admin
from firebase_admin import credentials, db

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")

# تهيئة Firebase
if not firebase_admin._apps:
    cred_path = os.getenv("FIREBASE_CREDENTIALS")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })

def get_user_data(user_id: int) -> dict:
    ref = db.reference(f"users/{user_id}")
    data = ref.get()
    return data or {"count": 0}

def set_user_data(user_id: int, data: dict):
    ref = db.reference(f"users/{user_id}")
    ref.set(data)

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    user_data = get_user_data(user_id)
    return user_data.get("count", 0) < limit

def increment_user_count(user_id: int):
    user_data = get_user_data(user_id)
    user_data["count"] = user_data.get("count", 0) + 1
    set_user_data(user_id, user_data)

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
