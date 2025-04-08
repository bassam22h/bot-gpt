import os
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from utils import get_total_users, load_users

ADMIN_ID = os.getenv("ADMIN_ID")
BROADCAST = range(1)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    num_users = get_total_users()
    await update.message.reply_text(f"إجمالي عدد المستخدمين: {num_users}")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("أرسل الرسالة التي تريد بثها لجميع المستخدمين:")
    return BROADCAST

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    message = update.message.text
    users = load_users()
    success = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            success += 1
        except Exception:
            pass

    await update.message.reply_text(f"تم إرسال الرسالة إلى {success} مستخدم.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء الإرسال.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def admin_handlers():
    return [
        CommandHandler("stats", show_stats),
        ConversationHandler(
            entry_points=[CommandHandler("broadcast", start_broadcast)],
            states={BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)]},
            fallbacks=[CommandHandler("cancel", cancel_broadcast)]
        )
    ]
