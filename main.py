import logging
import os
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
from config import TOKEN, ADMIN_ID  # قراءة ADMIN_ID من البيئة
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, PLATFORM_CHOICE, EVENT_DETAILS
from telegram import Update
from telegram.ext import CallbackContext

user_data = {}

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id == int(ADMIN_ID):  # التأكد من المقارنة بمعرف المشرف من البيئة
        update.message.reply_text("مرحبًا أيها المشرف، يمكنك الآن استخدام الأوامر الخاصة بالتحكم.")
    else:
        update.message.reply_text("مرحبًا بك في البوت!")

def send_to_all(update: Update, context: CallbackContext):
    if update.message.from_user.id == int(ADMIN_ID):
        message = ' '.join(context.args)
        for user_id in user_data:
            try:
                context.bot.send_message(chat_id=user_id, text=message)
            except:
                pass
        update.message.reply_text(f"تم إرسال الرسالة إلى جميع المستخدمين: {message}")
    else:
        update.message.reply_text("ليس لديك الصلاحيات لإرسال الرسائل.")

def stats(update: Update, context: CallbackContext):
    if update.message.from_user.id == int(ADMIN_ID):
        total_users = len(user_data)
        update.message.reply_text(f"إجمالي عدد المستخدمين: {total_users}")
    else:
        update.message.reply_text("ليس لديك الصلاحيات لعرض الإحصائيات.")

def main():
    logging.basicConfig(level=logging.INFO)
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_to_all", send_to_all))
    app.add_handler(CommandHandler("stats", stats))
    
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))

    conv = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post_handler)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT, event_details)],
        },
        fallbacks=[]
    )
    app.add_handler(conv)

    if os.getenv("RENDER"):
        app.run_webhook(
            listen="0.0.0.0",
            port=8443,
            url_path=TOKEN,
            webhook_url=f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
