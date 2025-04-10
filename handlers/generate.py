import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.openai_service import generate_response
from utils import (
    get_user_limit_status, increment_user_count,
    require_subscription, get_user_data, log_post
)

PLATFORM_CHOICE, EVENT_DETAILS = range(2)

SUPPORTED_PLATFORMS = ["تويتر", "لينكدإن", "إنستغرام"]
DAILY_LIMIT = 5

# قراءة معرفات المشرفين من متغير بيئة
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]

@require_subscription
async def generate_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    if not is_admin:
        count = get_user_data(user_id).get("count", 0)
        if count >= DAILY_LIMIT:
            await update.message.reply_text("⚠️ لقد وصلت للحد الأقصى من الطلبات اليوم.")
            return ConversationHandler.END

        remaining = DAILY_LIMIT - count
        await update.message.reply_text(
            f"📱 اختر المنصة:\n\nلديك {remaining} من {DAILY_LIMIT} طلبات متبقية اليوم.",
            reply_markup=ReplyKeyboardMarkup([SUPPORTED_PLATFORMS], one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "📱 اختر المنصة (لا يوجد حد للمشرفين):",
            reply_markup=ReplyKeyboardMarkup([SUPPORTED_PLATFORMS], one_time_keyboard=True, resize_keyboard=True)
        )

    return PLATFORM_CHOICE

@require_subscription
async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text

    if platform not in SUPPORTED_PLATFORMS:
        await update.message.reply_text("⚠️ المنصة غير مدعومة. اختر من القائمة.")
        return PLATFORM_CHOICE

    context.user_data["platform"] = platform
    await update.message.reply_text("✍️ أرسل الآن فكرة المنشور أو نصه:")
    return EVENT_DETAILS

@require_subscription
async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    platform = context.user_data.get("platform")
    user_input = update.message.text

    msg = await update.message.reply_text("⏳ يتم إنشاء المنشور...")

    try:
        result = generate_response(user_input, platform)

        if not is_admin:
            increment_user_count(user_id)
            remaining = max(0, DAILY_LIMIT - get_user_data(user_id).get("count", 0))
        else:
            remaining = "غير محدود"

        log_post(user_id, platform, result)

        await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update.message.reply_text(result)
        await update.message.reply_text(f"✅ تبقى لديك {remaining} من {DAILY_LIMIT} لهذا اليوم.")
    except Exception as e:
        await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update.message.reply_text("⚠️ حدث خطأ أثناء إنشاء المنشور. حاول مجددًا.")
        raise e

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END
