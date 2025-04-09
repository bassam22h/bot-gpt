import json
import os
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

USERS_FILE = "data/users.json"
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")

def ensure_data_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_users():
    ensure_data_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_users(users: dict):
    ensure_data_file()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user_limit_status(user_id: int, limit: int = 5) -> bool:
    users = load_users()
    count = users.get(str(user_id), 0)

    if isinstance(count, dict):
        count = count.get("count", 0)

    return count < limit

def increment_user_count(user_id: int):
    users = load_users()
    count = users.get(str(user_id), 0)

    if isinstance(count, dict):
        count = count.get("count", 0)

    users[str(user_id)] = count + 1
    save_users(users)

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
        except Exception as e:
            await update.message.reply_text("⚠️ حدث خطأ أثناء التحقق من الاشتراك.")
            return

        if not subscribed:
            await update.message.reply_text(
                f"❌ يجب عليك الاشتراك أولاً في القناة للاستفادة من خدمات البوت:\n\nhttps://t.me/{REQUIRED_CHANNEL.replace('@', '')}"
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper
