import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, date
from collections import Counter
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ============= تهيئة Firebase =============
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON")))
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("FIREBASE_DB_URL")
            })
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            raise

initialize_firebase()

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()

# ============= دوال الاشتراك =============
async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception as e:
        logger.error(f"Subscription check failed: {e}")
        return False

def require_subscription(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            user = None
            user_id = None

            # محاولة الحصول على المستخدم من مختلف أنواع التحديثات
            if update.effective_user:
                user = update.effective_user
                user_id = user.id
            elif update.message and update.message.from_user:
                user = update.message.from_user
                user_id = user.id
            elif update.callback_query and update.callback_query.from_user:
                user = update.callback_query.from_user
                user_id = user.id

            logger.debug(f"user: {user}, user_id: {user_id}")

            # التحقق من أن user_id صالح
            if user_id is None or not isinstance(user_id, int):
                logger.error("فشل في الحصول على user_id صالح.")
                return

            # التحقق من الاشتراك
            if not await is_user_subscribed(user_id, context):
                channel_name = REQUIRED_CHANNEL.replace('@', '')
                msg = (
                    f"🔐 للوصول إلى هذه الميزة، يرجى الاشتراك في قناتنا:\n\n"
                    f"https://t.me/{channel_name}\n\n"
                    "بعد الاشتراك، أعد المحاولة"
                )
                if update.message:
                    await update.message.reply_text(msg, disable_web_page_preview=True)
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.edit_message_text(msg, disable_web_page_preview=True)
                return

            return await func(update, context, *args, **kwargs)

        except Exception as e:
            logger.exception(f"Subscription decorator error: {e}")
            error_msg = "⚠️ حدث خطأ أثناء التحقق من الاشتراك"
            try:
                if update.message:
                    await update.message.reply_text(error_msg)
                elif update.callback_query:
                    await update.callback_query.answer(error_msg, show_alert=True)
            except Exception as nested_e:
                logger.error(f"Failed to send error message to user: {nested_e}")
    return wrapper

# ============= دوال المستخدمين =============
def get_all_users() -> dict:
    try:
        return db.reference("/users").get() or {}
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return {}

def get_user_data(user_id: int) -> dict:
    try:
        return db.reference(f"/users/{user_id}").get() or {
            "count": 0,
            "date": str(date.today()),
            "first_name": "",
            "username": "",
            "last_active": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return {"count": 0}

def save_user_data(user_id: int, data: dict):
    try:
        db.reference(f"/users/{user_id}").set(data)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    try:
        user_data = get_user_data(user_id)
        return user_data.get("count", 0) < limit
    except Exception as e:
        logger.error(f"Error checking user limit: {e}")
        return False

def has_reached_limit(user_id: int, limit: int = 5) -> bool:
    return not get_user_limit_status(user_id, limit)

def increment_user_count(user_id: int):
    try:
        user_ref = db.reference(f"/users/{user_id}")
        current_data = user_ref.get() or {}
        current_date = str(date.today())

        if current_data.get("date") != current_date:
            new_data = {
                "count": 1,
                "date": current_date,
                "last_active": str(datetime.utcnow())
            }
        else:
            new_data = {
                "count": current_data.get("count", 0) + 1,
                "last_active": str(datetime.utcnow())
            }

        user_ref.update(new_data)
    except Exception as e:
        logger.error(f"Error incrementing user count: {e}")

# ============= دوال المنشورات =============
def get_all_logs() -> dict:
    try:
        return db.reference("/logs").get() or {}
    except Exception as e:
        logger.error(f"Error getting all logs: {e}")
        return {}

def log_post(user_id: int, platform: str, content: str):
    try:
        post_ref = db.reference(f"/logs/{user_id}").push()
        post_ref.set({
            "platform": platform,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error logging post: {e}")

# ============= دوال الإحصائيات =============
def get_platform_usage(limit: int = 5) -> list:
    try:
        logs = get_all_logs()
        platforms = []
        
        for user_logs in logs.values():
            if isinstance(user_logs, dict):
                for post in user_logs.values():
                    if isinstance(post, dict) and post.get("platform"):
                        platforms.append(post["platform"])

        return Counter(platforms).most_common(limit) if platforms else []
    except Exception as e:
        logger.error(f"Error getting platform usage: {e}")
        return []

def get_daily_new_users() -> int:
    try:
        users = get_all_users()
        today = str(date.today())
        return sum(1 for u in users.values() if u.get('date') == today)
    except Exception as e:
        logger.error(f"Error getting daily new users: {e}")
        return 0

# ============= دوال الإدارة =============
def reset_user_counts():
    try:
        users_ref = db.reference("/users")
        users = users_ref.get() or {}
        updates = {f"{uid}/count": 0 for uid in users}
        users_ref.update(updates)
        logger.info("User counts reset successfully")
    except Exception as e:
        logger.error(f"Error resetting user counts: {e}")
        raise

def clear_all_logs():
    try:
        db.reference("/logs").delete()
        logger.info("All logs cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise
