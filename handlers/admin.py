from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton from telegram.ext import ContextTypes from utils import get_all_users_data, reset_all_users_data import os import logging from collections import Counter from datetime import datetime

ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_chat.id != ADMIN_ID: await update.message.reply_text("❌ ليس لديك صلاحية للوصول إلى لوحة المشرف.") return

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats")],
    [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="send_broadcast")],
    [InlineKeyboardButton("♻️ تصفير البيانات", callback_data="confirm_reset")]
])
await update.message.reply_text("🛠️ لوحة تحكم المشرف:", reply_markup=keyboard)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

if query.data == "show_stats":
    users = get_all_users_data()
    num_users = len(users)
    today = datetime.now().date()

    post_counts_today = 0
    platform_counter = Counter()

    for user_data in users.values():
        if "logs" in user_data:
            for log in user_data["logs"]:
                try:
                    log_date = datetime.fromisoformat(log["time"]).date()
                    if log_date == today:
                        post_counts_today += 1
                        platform_counter[log["platform"]] += 1
                except:
                    continue

    most_common = platform_counter.most_common(1)
    most_used_platform = most_common[0][0] if most_common else "لا توجد بيانات"

    await query.edit_message_text(
        f"👥 عدد المستخدمين: {num_users}\n"
        f"✍️ عدد المنشورات اليوم: {post_counts_today}\n"
        f"🔥 أكثر منصة استخدامًا: {most_used_platform}"
    )

elif query.data == "send_broadcast":
    context.user_data["awaiting_broadcast"] = True
    await query.edit_message_text("✏️ أرسل الآن الرسالة التي تريد بثها لجميع المستخدمين:")

elif query.data == "confirm_reset":
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نعم، تأكيد التصفير", callback_data="do_reset")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_reset")]
    ])
    await query.edit_message_text("⚠️ هل أنت متأكد أنك تريد تصفير كل البيانات؟", reply_markup=keyboard)

elif query.data == "do_reset":
    reset_all_users_data()
    await query.edit_message_text("✅ تم تصفير جميع بيانات المستخدمين بنجاح.")

elif query.data == "cancel_reset":
    await query.edit_message_text("❌ تم إلغاء عملية التصفير.")

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_chat.id != ADMIN_ID or not context.user_data.get("awaiting_broadcast"): return

message = update.message.text
context.user_data["awaiting_broadcast"] = False

users = get_all_users_data()
count = 0
for user_id in users:
    try:
        await context.bot.send_message(chat_id=int(user_id), text=message)
        count += 1
    except Exception as e:
        logging.error(f"خطأ في الإرسال للمستخدم {user_id}: {e}")

await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")

