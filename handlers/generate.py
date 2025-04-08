from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from services.openai_service import generate_post
from utils import get_user_limit_status, increment_user_count

PLATFORM_CHOICE, EVENT_DETAILS = range(2)

async def generate_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_user_limit_status(user_id):
        await update.message.reply_text("⚠️ لقد وصلت للحد الأقصى من الطلبات اليوم.")
        return ConversationHandler.END

    keyboard = [["تويتر", "لينكدإن", "إنستغرام"]]
    await update.message.reply_text(
        "📱 اختر المنصة:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return PLATFORM_CHOICE

async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text
    context.user_data["platform"] = platform
    await update.message.reply_text("✍️ أرسل الآن فكرة المنشور أو نصه:")
    return EVENT_DETAILS

async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    platform = context.user_data.get("platform")
    user_input = update.message.text

    msg = await update.message.reply_text("⏳ يتم إنشاء المنشور، الرجاء الانتظار...")

    result = await generate_post(user_input, platform)
    increment_user_count(user_id)

    await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
    await update.message.reply_text(result)
    return ConversationHandler.END
