import json
import os
from datetime import datetime
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

USERS_FILE = "data/users.json"
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # تأكد أنه بدون @ في .env

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

# ديكوريتر التحقق من الاشتراك
def require_subscription(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        try:
            # التحقق من الاشتراك باستخدام اسم المستخدم للقناة
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await func(update, context, *args, **kwargs)
            else:
                await update.effective_message.reply_text(
                    f"⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.\n\n"
                    f"اشترك هنا: https://t.me/{CHANNEL_USERNAME}\n"
                    "ثم أعد المحاولة."
                )
        except:
            await update.effective_message.reply_text(
                "⚠️ حدث خطأ أثناء التحقق من الاشتراك. تأكد أن البوت مشرف في القناة."
            )
    return wrapper
