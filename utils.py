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

# متغيرات القناة المطلوبة
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()

# ========== دوال إدارة الاشتراكات ==========
async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القناة المطلوبة"""
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception as e:
        logger.error(f"Subscription check failed for {user_id}: {e}")
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
                    f"⛔️ للوصول إلى هذه الميزة، يرجى الاشتراك في قناتنا أولاً:\n\n"
                    f"https://t.me/{channel_name}\n\n"
                    "بعد الاشتراك، أعد المحاولة",
                    disable_web_page_preview=True
                )
                return
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Subscription requirement failed: {e}")
            await update.message.reply_text("⚠️ حدث خطأ أثناء التحقق من الاشتراك")
    return wrapper

# ========== دوال إدارة المستخدمين ==========
def get_user_data(user_id: int):
    """جلب بيانات المستخدم من Firebase"""
    try:
        return db.reference(f"/users/{user_id}").get() or {
            "count": 0, 
            "date": str(date.today()),
            "first_name": "",
            "username": "",
            "last_active": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Error getting user data for {user_id}: {e}")
        return {"count": 0}

def save_user_data(user_id: int, data: dict):
    """حفظ بيانات المستخدم في Firebase"""
    try:
        db.reference(f"/users/{user_id}").set(data)
    except Exception as e:
        logger.error(f"Error saving data for {user_id}: {e}")

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    """التحقق من إذا كان المستخدم لم يتجاوز الحد اليومي"""
    try:
        user_data = get_user_data(user_id)
        return user_data.get("count", 0) < limit
    except Exception as e:
        logger.error(f"Error checking limit for {user_id}: {e}")
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
        logger.error(f"Error incrementing count for {user_id}: {e}")

# ========== دوال إدارة السجلات ==========
def log_post(user_id: int, platform: str, content: str):
    """تسجيل المنشور في قاعدة البيانات"""
    try:
        post_ref = db.reference(f"/logs/{user_id}").push()
        post_ref.set({
            "platform": platform,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error logging post for {user_id}: {e}")

def get_all_logs():
    """جلب جميع سجلات المنشورات"""
    try:
        return db.reference("/logs").get() or {}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return {}

# ========== دوال الإحصائيات ==========
def get_platform_usage(limit=5):
    """جلب إحصائيات استخدام المنصات"""
    try:
        logs = get_all_logs()
        platforms = []
        
        for user_logs in logs.values():
            if not isinstance(user_logs, dict):
                continue
                
            for post in user_logs.values():
                if isinstance(post, dict) and post.get("platform"):
                    platforms.append(post["platform"])

        if not platforms:
            return []

        return Counter(platforms).most_common(limit)
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return []

def reset_user_counts():
    """تصفير جميع عدادات المستخدمين"""
    try:
        users_ref = db.reference("/users")
        users = users_ref.get() or {}
        
        updates = {f"{uid}/count": 0 for uid in users}
        users_ref.update(updates)
        logger.info("Successfully reset all user counts")
    except Exception as e:
        logger.error(f"Error resetting counts: {e}")
        raise

def clear_all_logs():
    """حذف جميع سجلات المنشورات"""
    try:
        db.reference("/logs").delete()
        logger.info("Successfully cleared all logs")
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise

# ========== دوال أخرى ==========
def get_daily_new_users():
    """جلب عدد المستخدمين الجدد اليوم"""
    try:
        users = db.reference("/users").get() or {}
        today = str(date.today())
        return sum(1 for u in users.values() if u.get('date') == today)
    except Exception as e:
        logger.error(f"Error getting new users: {e}")
        return 0
