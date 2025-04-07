import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from openai import OpenAI  # OpenAI API الجديد

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PLATFORM_CHOICE, EVENT_DETAILS = range(2)

# Platform character limits
PLATFORM_LIMITS = {
    "Twitter": 280,
    "LinkedIn": 3000,
    "Instagram": 2200
}

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
    🚀 Welcome to Social Media Post Generator! 
    Use /generate to create amazing posts for:
    - Twitter (280 chars)
    - LinkedIn (3000 chars)
    - Instagram (2200 chars)
    """
    await update.message.reply_text(welcome_text)

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Twitter", "LinkedIn", "Instagram"]]
    await update.message.reply_text(
        "Choose a platform:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True,
            input_field_placeholder="Platform?"
        )
    )
    return PLATFORM_CHOICE

async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["platform"] = update.message.text
    await update.message.reply_text("📝 Describe your event/details:")
    return EVENT_DETAILS

async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    platform = context.user_data["platform"]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # أو "gpt-4" إذا كنت تريد استخدام GPT-4
            messages=[
                {"role": "system", "content": f"Generate engaging social media post for {platform} in the same language as the user's input. Include relevant emojis. Max {PLATFORM_LIMITS[platform]} characters."},
                {"role": "user", "content": user_input}
            ]
        )
        
        generated_text = response.choices[0].message.content
        
        # Validate character limit
        if len(generated_text) > PLATFORM_LIMITS[platform]:
            warning = f"⚠️ Warning: Post exceeds {PLATFORM_LIMITS[platform]} characters ({len(generated_text)})"
            await update.message.reply_text(warning)
        
        await update.message.reply_text(generated_text)
        
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        await update.message.reply_text("❌ Error generating post. Please try again.")
    
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT, event_details)]
        },
        fallbacks=[]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # For Render deployment
    if os.getenv("RENDER"):
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8443)),
            url_path=TOKEN,
            webhook_url=f"https://social-bot-qmf3.onrender.com/{TOKEN}"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
