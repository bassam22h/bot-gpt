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

# إعداد المسجل (logger)
logger = logging.getLogger(__name__)

# تهيئة Firebase
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

# إعدادات القناة المطلوبة
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()

# ============= دوال الاشتراك =============
async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception as e:
        logger.error(f"Subscription check failed: {e}")
        return False

def require_subscription(func):
    """ديكوراتور للتحقق من الاشتراك قبل تنفيذ الأمر"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            if not await is_user_subscribed(user_id, context):
                channel_name = REQUIRED_CHANNEL.replace('@', '')
                await update.message.reply_text(
                    f"🔐 للوصول إلى هذه الميزة، يرجى الاشتراك في قناتنا:\n\n"
                    f"https://t.me/{channel_name}\n\n"
                    "بعد الاشتراك، أعد المحاولة",
                    disable_web_page_preview=True
                )
                return
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Subscription decorator error: {e}")
            await update.message.reply_text("⚠️ حدث خطأ أثناء التحقق من الاشتراك")
    return wrapper

# ============= دوال المستخدمين =============
def get_all_users() -> dict:
    """جلب جميع المستخدمين"""
    try:
        return db.reference("/users").get() or {}
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return {}

def get_user_data(user_id: int) -> dict:
    """جلب بيانات مستخدم معين"""
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
    """حفظ بيانات المستخدم"""
    try:
        db.reference(f"/users/{user_id}").set(data)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    """التحقق من عدم تجاوز الحد اليومي"""
    try:
        user_data = get_user_data(user_id)
        return user_data.get("count", 0) < limit
    except Exception as e:
        logger.error(f"Error checking user limit: {e}")
        return False

def increment_user_count(user_id: int):
    """زيادة عداد استخدامات المستخدم"""
    try:
        user_ref = db.reference(f"/users/{user_id}")
        user_ref.update({
            "count": firebase_admin.db.Increment(1),
            "last_active": str(datetime.utcnow())
        })
    except Exception as e:
        logger.error(f"Error incrementing user count: {e}")

# ============= دوال المنشورات =============
def get_all_logs() -> dict:
    """جلب جميع سجلات المنشورات"""
    try:
        return db.reference("/logs").get() or {}
    except Exception as e:
        logger.error(f"Error getting all logs: {e}")
        return {}

def log_post(user_id: int, platform: str, content: str):
    """تسجيل منشور جديد"""
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
    """ترتيب المنصات حسب الاستخدام"""
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
    """عدد المستخدمين الجدد اليوم"""
    try:
        users = get_all_users()
        today = str(date.today())
        return sum(1 for u in users.values() if u.get('date') == today)
    except Exception as e:
        logger.error(f"Error getting daily new users: {e}")
        return 0

# ============= دوال الإدارة =============
def reset_user_counts():
    """تصفير جميع عدادات المستخدمين"""
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
    """حذف جميع سجلات المنشورات"""
    try:
        db.reference("/logs").delete()
        logger.info("All logs cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise
