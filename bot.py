import os
import logging
from datetime import datetime, timedelta
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

# تخزين طلبات المستخدمين
user_requests = {}

# حدود الأحرف لكل منصة (مخفي الآن)
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
    - تويتر
    - لينكدإن
    - إنستغرام

    ⚠️ الحد المسموح: 5 طلبات يومياً لكل مستخدم
    """
    await update.message.reply_text(welcome_text)

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # التحقق من عدد الطلبات
    if not check_user_limit(user_id):
        await update.message.reply_text("⚠️ لقد وصلت إلى الحد الأقصى من الطلبات لهذا اليوم (5 طلبات).")
        return ConversationHandler.END
        
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

def check_user_limit(user_id):
    today = datetime.now().date()
    if user_id not in user_requests:
        user_requests[user_id] = {'date': today, 'count': 0}
    
    if user_requests[user_id]['date'] != today:
        user_requests[user_id] = {'date': today, 'count': 0}
    
    return user_requests[user_id]['count'] < 5

async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text
    context.user_data["platform"] = platform
    await update.message.reply_text(
        f"✍️ الآن، اكتب محتوى المنشور الذي تريد إنشاؤه لـ {platform}:\n"
        "(سيتم إعلامك عند اكتمال الإنشاء)"
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
                    "content": f"أنشئ منشورًا لـ {platform} باللغة العربية. استخدم إيموجيز واجعل المحتوى جذابًا."
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
    user_id = update.message.from_user.id
    user_input = update.message.text
    platform = context.user_data["platform"]
    
    # إرسال رسالة الانتظار
    wait_msg = await update.message.reply_text("⏳ جاري إنشاء المنشور، يرجى الانتظار...")
    
    try:
        # زيادة عدد الطلبات
        user_requests[user_id]['count'] += 1
        
        generated_text = await generate_post_content(user_input, platform)
        
        # حذف رسالة الانتظار
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=wait_msg.message_id)
        
        # إرسال المنشور النهائي بدون أي إضافات
        await update.message.reply_text(generated_text)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء المنشور. يرجى المحاولة لاحقًا.")
    
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
