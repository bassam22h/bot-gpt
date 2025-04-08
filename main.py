import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from config import TOKEN
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, PLATFORM_CHOICE, EVENT_DETAILS
from handlers.admin import admin_handlers

def main():
    logging.basicConfig(level=logging.INFO)
    webhook_url = f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    # أوامر المستخدم العادي
    app.add_handler(CommandHandler("start", start_handler))
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

    # أوامر المشرف
    for handler in admin_handlers():
        app.add_handler(handler)

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
