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
from openai import OpenAI

# إعدادات البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PLATFORM_CHOICE, EVENT_DETAILS = range(2)

# حدود الأحرف لكل منصة
PLATFORM_LIMITS = {
    "تويتر": 280,
    "لينكدإن": 3000,
    "إنستغرام": 2200
}

# تهيئة عميل OpenAI مع OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
    🎉 أهلاً بك في بوت إنشاء المنشورات الذكي!

    ✨ يمكنك إنشاء منشورات احترافية لوسائل التواصل الاجتماعي بسهولة.

    📌 كيفية الاستخدام:
    1. اضغط /generate لبدء إنشاء منشور جديد
    2. اختر المنصة المطلوبة
    3. اكتب محتوى المنشور أو الفكرة الرئيسية
    4. سيقوم البوت بإرسال المنشور الجاهز لك

    🏆 المنصات المدعومة:
    - تويتر (280 حرفًا كحد أقصى)
    - لينكدإن (3000 حرفًا كحد أقصى)
    - إنستغرام (2200 حرفًا كحد أقصى)

    💡 يمكنك إضافة إيموجيز وتنسيق النص كما تريد!
    """
    await update.message.reply_text(welcome_text)

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["تويتر", "لينكدإن", "إنستغرام"]]
    await update.message.reply_text(
        "📱 اختر منصة التواصل الاجتماعي:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="اختر منصة..."
        )
    )
    return PLATFORM_CHOICE

async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text
    context.user_data["platform"] = platform
    await update.message.reply_text(
        f"✍️ الآن، اكتب محتوى المنشور الذي تريد إنشاؤه لـ {platform}:\n"
        "(يمكنك كتابة فكرة عامة أو نقاط رئيسية)"
    )
    return EVENT_DETAILS

async def generate_post_content(user_input: str, platform: str) -> str:
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://social-bot.com",
                "X-Title": "Telegram Social Bot",
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "system",
                    "content": f"أنت مساعد لإنشاء منشورات لـ {platform}. أنشئ منشورًا جذابًا باللغة العربية مع إيموجيز مناسبة. الحد الأقصى {PLATFORM_LIMITS[platform]} حرف."
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenRouter Error: {e}")
        raise

async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    platform = context.user_data["platform"]
    
    try:
        generated_text = await generate_post_content(user_input, platform)
        
        if len(generated_text) > PLATFORM_LIMITS[platform]:
            warning = f"⚠️ تنبيه: تجاوز عدد الأحرف المسموح به ({PLATFORM_LIMITS[platform]} حرف)"
            await update.message.reply_text(warning)
        
        await update.message.reply_text("✅ تم إنشاء المنشور بنجاح:\n\n" + generated_text)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء المنشور. يرجى المحاولة لاحقًا.\n"
            "إذا استمرت المشكلة، تأكد من أنك لم تتجاوز الحد المسموح من الطلبات."
        )
    
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
    
    # إعدادات النشر على Render
    if os.getenv("RENDER"):
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8443)),
            url_path=TOKEN,
            webhook_url=f"https://bassam-bot-soc.onrender.com/{TOKEN}"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
