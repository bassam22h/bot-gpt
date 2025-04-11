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
            logger.error(f"فشل تهيئة Firebase: {e}")
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
        logger.error(f"فشل التحقق من الاشتراك: {e}")
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
            logger.error(f"خطأ في ديكوراتور الاشتراك: {e}")
            await update.message.reply_text("⚠️ حدث خطأ أثناء التحقق من الاشتراك")
    return wrapper

# ============= دوال المستخدمين =============
def get_user_data(user_id: int) -> dict:
    """جلب بيانات المستخدم"""
    try:
        return db.reference(f"/users/{user_id}").get() or {
            "count": 0,
            "date": str(date.today()),
            "first_name": "",
            "username": "",
            "last_active": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات المستخدم {user_id}: {e}")
        return {"count": 0}

def save_user_data(user_id: int, data: dict):
    """حفظ بيانات المستخدم"""
    try:
        db.reference(f"/users/{user_id}").set(data)
    except Exception as e:
        logger.error(f"خطأ في حفظ بيانات المستخدم {user_id}: {e}")

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    """التحقق من عدم تجاوز الحد اليومي"""
    try:
        user_data = get_user_data(user_id)
        return user_data.get("count", 0) < limit
    except Exception as e:
        logger.error(f"خطأ في التحقق من الحد {user_id}: {e}")
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
        logger.error(f"خطأ في زيادة العداد {user_id}: {e}")

# ============= دوال المنشورات =============
def log_post(user_id: int, platform: str, content: str):
    """تسجيل المنشور في السجلات"""
    try:
        post_ref = db.reference(f"/logs/{user_id}").push()
        post_ref.set({
            "platform": platform,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"خطأ في تسجيل المنشور {user_id}: {e}")

def get_all_logs() -> dict:
    """جلب جميع سجلات المنشورات"""
    try:
        return db.reference("/logs").get() or {}
    except Exception as e:
        logger.error(f"خطأ في جلب السجلات: {e}")
        return {}

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
        logger.error(f"خطأ في جلب إحصائيات المنصات: {e}")
        return []

def reset_user_counts():
    """تصفير جميع العدادات"""
    try:
        users_ref = db.reference("/users")
        users = users_ref.get() or {}
        updates = {f"{uid}/count": 0 for uid in users}
        users_ref.update(updates)
        logger.info("تم تصفير العدادات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تصفير العدادات: {e}")
        raise

def clear_all_logs():
    """حذف جميع السجلات"""
    try:
        db.reference("/logs").delete()
        logger.info("تم حذف السجلات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في حذف السجلات: {e}")
        raise

# ============= دوال أخرى =============
def get_daily_new_users() -> int:
    """عدد المستخدمين الجدد اليوم"""
    try:
        users = db.reference("/users").get() or {}
        today = str(date.today())
        return sum(1 for u in users.values() if u.get('date') == today)
    except Exception as e:
        logger.error(f"خطأ في جلب المستخدمين الجدد: {e}")
        return 0
