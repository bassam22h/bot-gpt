import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters
)
from config import TOKEN, ADMIN_ID
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, PLATFORM_CHOICE, EVENT_DETAILS

async def send_message_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ليس لديك صلاحية للقيام بهذا الأمر.")
        return

    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("من فضلك، أرسل رسالة لإرسالها لجميع المستخدمين.")
        return

    try:
        with open("data/users.json", "r") as f:
            users = list(set(json.load(f)))
    except:
        users = []

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logging.error(f"فشل في الإرسال للمستخدم {user_id}: {e}")

    await update.message.reply_text(f"تم إرسال الرسالة إلى {len(users)} مستخدم.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Received /stats command from chat ID: {update.effective_chat.id}")

    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("ليس لديك صلاحية لعرض الإحصاءات.")
        return

    try:
        with open("data/users.json", "r") as f:
            users = list(set(json.load(f)))
        num_users = len(users)
    except:
        num_users = 0

    await update.message.reply_text(f"إجمالي عدد المستخدمين: {num_users}")

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error occurred: {context.error}")

def main():
    logging.basicConfig(level=logging.INFO)

    webhook_url = f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))

    conv = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post_handler)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_details)],
        },
        fallbacks=[]
    )
    app.add_handler(conv)

    # أوامر المشرف
    app.add_handler(CommandHandler("send_all", send_message_to_all))
    app.add_handler(CommandHandler("stats", show_stats))

    app.add_error_handler(error_handler)

    if os.getenv("RENDER"):
        app.run_webhook(
            listen="0.0.0.0",
            port=8443,
            url_path=TOKEN,
            webhook_url=webhook_url
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
