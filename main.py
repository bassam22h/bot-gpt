import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler,
    MessageHandler, ContextTypes, filters
)
from config import TOKEN, ADMIN_ID
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, cancel, PLATFORM_CHOICE, EVENT_DETAILS
from handlers.admin import admin_panel, handle_admin_actions, receive_broadcast_message

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error occurred: {context.error}")

def main():
    logging.basicConfig(level=logging.INFO)

    webhook_url = f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))

    # المحادثة الخاصة بإنشاء منشور
    conv = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post_handler)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv)

    # أوامر المشرف
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^(show_stats|send_broadcast)$"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_ID), receive_broadcast_message))

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
