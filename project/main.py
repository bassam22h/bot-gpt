import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
from config import TOKEN
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, PLATFORM_CHOICE, EVENT_DETAILS

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

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
    app.run_polling()

if __name__ == "__main__":
    main()
