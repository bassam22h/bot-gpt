from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from firebase_admin import db
import os
import logging

ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية للوصول إلى لوحة المشرف.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="send_broadcast")]
    ])
    await update.message.reply_text("🛠️ لوحة تحكم المشرف:", reply_markup=keyboard)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_stats":
        try:
            ref = db.reference("/users")
            users = ref.get() or {}
            num_users = len(users)
        except Exception as e:
            logging.error(f"خطأ في جلب الإحصائيات: {e}")
            num_users = 0

        await query.edit_message_text(f"👥 عدد المستخدمين: {num_users}")

    elif query.data == "send_broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("✏️ أرسل الآن الرسالة التي تريد بثها لجميع المستخدمين:")

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID or not context.user_data.get("awaiting_broadcast"):
        return

    message = update.message.text
    context.user_data["awaiting_broadcast"] = False

    try:
        ref = db.reference("/users")
        users = ref.get() or {}
    except Exception as e:
        logging.error(f"خطأ في تحميل المستخدمين من Firebase: {e}")
        users = {}

    count = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            count += 1
        except Exception as e:
            logging.error(f"خطأ في الإرسال للمستخدم {user_id}: {e}")

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")
