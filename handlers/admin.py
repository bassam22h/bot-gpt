from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import os
import logging
from datetime import datetime
from utils import get_all_users, get_all_logs, clear_all_users

ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="send_broadcast")],
        [InlineKeyboardButton("🧹 تصفير المستخدمين", callback_data="clear_users")]
    ])
    await update.message.reply_text("🛠️ لوحة تحكم المشرف:", reply_markup=keyboard)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_stats":
        users = get_all_users()
        logs = get_all_logs()

        num_users = len(users)
        all_posts = []
        posts_today = 0
        platform_counter = {}

        today = datetime.utcnow().date()

        for user_id, user_logs in logs.items():
            for ts, log in user_logs.items():
                all_posts.append(log)
                if "platform" in log:
                    platform = log["platform"]
                    platform_counter[platform] = platform_counter.get(platform, 0) + 1
                try:
                    log_time = datetime.fromisoformat(ts).date()
                    if log_time == today:
                        posts_today += 1
                except:
                    continue

        most_common_platform = max(platform_counter.items(), key=lambda x: x[1])[0] if platform_counter else "غير محدد"

        text = (
            f"👥 المستخدمون: {num_users}\n"
            f"📝 إجمالي المنشورات: {len(all_posts)}\n"
            f"📅 منشورات اليوم: {posts_today}\n"
            f"🔥 أكثر منصة استخدامًا: {most_common_platform}"
        )
        await query.edit_message_text(text)

    elif query.data == "send_broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("✏️ أرسل الرسالة التي تريد بثها:")

    elif query.data == "clear_users":
        clear_all_users()
        await query.edit_message_text("✅ تم حذف جميع بيانات المستخدمين.")

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID or not context.user_data.get("awaiting_broadcast"):
        return

    message = update.message.text
    context.user_data["awaiting_broadcast"] = False

    users = get_all_users()
    count = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            count += 1
        except Exception as e:
            logging.error(f"فشل الإرسال إلى {user_id}: {e}")

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")
