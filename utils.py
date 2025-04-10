import os
import json
import firebase_admin
from firebase_admin import credentials, db
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, date
from collections import Counter, defaultdict

FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_DB_URL = "https://ai-postmakerbot-default-rtdb.asia-southeast1.firebasedatabase.app"
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")

# تهيئة Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DB_URL
    })

# بيانات المستخدمين
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

# الاشتراك بالقناة
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
                f"❌ يجب عليك الاشتراك أولاً في القناة:\n\nhttps://t.me/{REQUIRED_CHANNEL.replace('@', '')}"
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

# تسجيل المنشورات
def log_post(user_id: int, platform: str, content: str):
    timestamp = datetime.utcnow().isoformat()
    sanitized_timestamp = timestamp.replace(".", "-")  # تصحيح العلامات غير المسموح بها
    ref = db.reference(f"/logs/{user_id}/{sanitized_timestamp}")
    ref.set({
        "platform": platform,
        "content": content
    })

# الإحصائيات
def get_all_users():
    ref = db.reference("/users")
    return ref.get() or {}

def get_all_logs():
    ref = db.reference("/logs")
    return ref.get() or {}

# المستخدمين الجدد يوميًا
def get_daily_new_users():
    users = get_all_users()
    daily_counts = defaultdict(int)
    for data in users.values():
        join_date = data.get("date")
        if join_date:
            daily_counts[join_date] += 1
    return dict(sorted(daily_counts.items(), reverse=True))

# ترتيب المنصات حسب الاستخدام
def get_platform_usage():
    logs = get_all_logs()
    platforms = []
    for user_id, user_logs in logs.items():  # التكرار عبر جميع سجلات المستخدمين
        if isinstance(user_logs, dict):
            for timestamp, entry in user_logs.items():  # التكرار عبر جميع الإدخالات
                if isinstance(entry, dict) and "platform" in entry:
                    platforms.append(entry["platform"])  # إضافة المنصة
        else:
            print(f"Unexpected format for user {user_id}: {user_logs}")
    
    if platforms:  # تأكد من أن المنصات تحتوي على بيانات
        counter = Counter(platforms)  # حساب تكرار المنصات
        return dict(counter.most_common())  # إرجاع المنصات مرتبة
    else:
        return []  # إرجاع قائمة فارغة إذا لم توجد منصات

# تصفير العدادات فقط دون حذف المستخدمين
def reset_user_counts():
    users_ref = db.reference("/users")
    users_data = users_ref.get() or {}

    for user_id in users_data:
        users_data[user_id]["count"] = 0

    users_ref.set(users_data)

# حذف كل السجلات (المنشورات)
def clear_all_logs():
    ref = db.reference("/logs")
    ref.delete()

# إضافة دالة get_new_users_today لحساب عدد المستخدمين الجدد اليوم
def get_new_users_today(users):
    today = str(datetime.utcnow().date())  # الحصول على تاريخ اليوم
    new_users_count = 0

    for user_data in users.values():
        if user_data.get("date") == today:  # التحقق إذا كان تاريخ انضمام المستخدم هو اليوم
            new_users_count += 1

    return new_users_count
