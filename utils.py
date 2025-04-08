import os
import logging
from telegram import Bot, Update
from telegram.ext import ContextTypes
from datetime import datetime
import json

# جلب متغيرات البيئة
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
USERS_FILE = "data/users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user_limit_status(user_id):
    users = load_users()
    today = str(datetime.utcnow().date())

    if str(user_id) not in users:
        users[str(user_id)] = {"date": today, "count": 0}
        save_users(users)
        return True

    user_data = users[str(user_id)]
    if user_data["date"] != today:
        users[str(user_id)] = {"date": today, "count": 0}
        save_users(users)
        return True

    return user_data["count"] < 5

def increment_user_count(user_id):
    users = load_users()
    today = str(datetime.utcnow().date())

    if str(user_id) not in users or users[str(user_id)]["date"] != today:
        users[str(user_id)] = {"date": today, "count": 1}
    else:
        users[str(user_id)]["count"] += 1

    save_users(users)

def get_total_users():
    users = load_users()
    return len(users)

# التحقق من الاشتراك في القناة
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من اشتراك المستخدم في القناة."""
    user_id = update.effective_user.id
    bot = context.bot

    try:
        # التحقق من الاشتراك في القناة باستخدام اسم المستخدم
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True  # المستخدم مشترك في القناة
        else:
            return False  # المستخدم غير مشترك في القناة
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False  # إذا حدث خطأ في التحقق، يُعتبر غير مشترك

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع أمر /start."""
    if await check_subscription(update, context):
        await update.message.reply_text("✅ مرحبًا بك! أنت مشترك في القناة.")
    else:
        await update.message.reply_text("⚠️ يجب أن تشترك في القناة أولاً.")
