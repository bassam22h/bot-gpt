import os
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from openai import OpenAI

# إعدادات البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PLATFORM_CHOICE, EVENT_DETAILS = range(2)

# إعدادات القناة الإجبارية (استبدل بالقيم الحقيقية)
CHANNEL_USERNAME = "@aitools_ar"  # مثال: "@MySocialChannel"
CHANNEL_LINK = "https://t.me/aitools_ar"  # مثال: "https://t.me/MySocialChannel"

# تخزين طلبات المستخدمين
user_requests = {}

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

### الدوال الجديدة لنظام الاشتراك ###
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """تحقق مما إذا كان المستخدم مشتركًا في القناة"""
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user.id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أرسل رسالة تطلب الاشتراك"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_subscription")]
    ])
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔒 للوصول إلى جميع ميزات البوت، يجب الاشتراك في قناتنا:\n"
             f"{سوق الرقميات}\n\n"
             "بعد الاشتراك، اضغط على زر 'تم الاشتراك' للتأكيد",
        reply_markup=keyboard
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحقق من الاشتراك عند الضغط على الزر"""
    query = update.callback_query
    await query.answer()
    
    if await check_subscription(update, context):
        await query.edit_message_text("🎉 تم التحقق من اشتراكك بنجاح! يمكنك الآن استخدام البوت عبر /start")
        await start(update, context)
    else:
        await query.edit_message_text("❌ لم نتمكن من التحقق من اشتراكك. تأكد من:\n1. الاشتراك في القناة\n2. عدم إخفاء اشتراكك\nثم اضغط الزر مرة أخرى")

### الدوال الأصلية (تم تعديلها لدعم نظام الاشتراك) ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    welcome_text = """
    🎉 أهلاً بك في بوت إنشاء المنشورات الذكي!

    ✨ يمكنك إنشاء منشورات احترافية لوسائل التواصل الاجتماعي بسهولة.

    📌 كيفية الاستخدام:
    1. اضغط /generate لبدء إنشاء منشور جديد
    2. اختر المنصة المطلوبة
    3. اكتب محتوى المنشور أو الفكرة الرئيسية
    4. سيقوم البوت بإرسال المنشور الجاهز لك

    🏆 المنصات المدعومة:
    - تويتر (منشورات قصيرة)
    - لينكدإن (منشورات متوسطة)
    - إنستغرام (منشورات طويلة)

    ⚠️ الحد المسموح: 5 طلبات يومياً لكل مستخدم
    """
    await update.message.reply_text(welcome_text)

async def generate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    user_id = update.message.from_user.id
    
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

### الدوال الأصلية (بدون تعديلات) ###
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
        "(يمكنك كتابة فكرة عامة أو نقاط رئيسية)"
    )
    return EVENT_DETAILS

async def generate_post_content(user_input: str, platform: str) -> str:
    try:
        system_prompt = f"""أنت مساعد محترف لإنشاء منشورات على {platform}. اتبع هذه التعليمات:
        - اكتب محتوى عالي الجودة باللغة العربية الفصحى
        - استخدم لغة سهلة وجذابة
        - لا تستخدم أي تنسيقات Markdown مثل ** أو __
        - استخدم 3-5 إيموجيز بشكل مناسب
        - اجعل الجمل قصيرة وواضحة
        - تجنب التكرار واستخدم مرادفات متنوعة
        - التركيز على المعلومات الفريدة والمثيرة للاهتمام"""
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://social-bot.com",
                "X-Title": "Telegram Social Bot",
                "X-Data-Policy": "train"
            },
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        
        clean_text = completion.choices[0].message.content
        clean_text = re.sub(r'[\*\_\#\~]', '', clean_text)
        return clean_text.strip()
        
    except Exception as e:
        logging.error(f"OpenRouter Error: {e}")
        raise

async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_input = update.message.text
    platform = context.user_data["platform"]
    
    wait_msg = await update.message.reply_text("⏳ جاري معالجة طلبك، الرجاء الانتظار...")
    
    try:
        if not check_user_limit(user_id):
            await update.message.reply_text("⚠️ لقد تجاوزت الحد اليومي للطلبات.")
            return ConversationHandler.END
            
        user_requests[user_id]['count'] += 1
        generated_text = await generate_post_content(user_input, platform)
        
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=wait_msg.message_id
        )
        
        if len(generated_text) > 1000:
            parts = [generated_text[i:i+1000] for i in range(0, len(generated_text), 1000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(generated_text)
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء المنشور. يرجى المحاولة لاحقًا.\n"
            "إذا استمرت المشكلة، تأكد من أنك لم تتجاوز الحد المسموح من الطلبات."
        )
    
    return ConversationHandler.END

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # إضافة معالج الاشتراك الجديد
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    
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
