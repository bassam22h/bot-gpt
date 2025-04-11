import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)
from config import TOKEN, ADMIN_IDS
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import (
    generate_post_handler, platform_choice,
    event_details, cancel, PLATFORM_CHOICE, EVENT_DETAILS
)
from handlers.admin import (
    admin_panel, handle_admin_actions,
    receive_broadcast_message
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and hasattr(update, 'message'):
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع. الرجاء المحاولة لاحقًا.")

def setup_handlers(app):
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post_handler)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)

    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^(view_statistics|reset_counts_|clear_logs_|broadcast_)"))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_IDS), receive_broadcast_message))

def main():
    app = ApplicationBuilder().token(TOKEN).webhook_path(f"/{TOKEN}").build()
    setup_handlers(app)
    app.add_error_handler(error_handler)

    if os.getenv("RENDER"):
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8443)),
            webhook_url=f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}",
            secret_token=os.getenv("WEBHOOK_SECRET", "")
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
